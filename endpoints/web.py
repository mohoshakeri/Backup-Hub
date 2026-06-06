from pathlib import Path
from typing import Any
from urllib.parse import quote

from fastapi import APIRouter, Request, Response, status
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from services.auth import (
    create_csrf_token,
    create_login_csrf_token,
    create_session_token,
    validate_login_csrf_token,
    validate_csrf_token,
    validate_password,
    validate_session_token,
    validate_totp,
)
from services.backups import get_backup_or_none, list_backups
from services.download_tokens import create_download_token, validate_download_token
from utils.config import (
    COOKIE_SECURE,
    FAVICON_URL,
    LOGO_URL,
    PROJECT_ROOT,
    SESSION_COOKIE,
    SESSION_TTL_SECONDS,
    USE_NGINX_ACCEL,
)

router: APIRouter = APIRouter(tags=["Web"])
templates: Jinja2Templates = Jinja2Templates(directory=str(PROJECT_ROOT / "templates"))
LOGIN_CSRF_COOKIE: str = "{}_login_csrf".format(SESSION_COOKIE)


@router.get("/", response_class=HTMLResponse)
async def index(request: Request) -> HTMLResponse:
    if not _is_authenticated(request=request):
        return _login_page(request=request)

    backups: list[Path] = list_backups()
    return _dashboard_page(request=request, backups=backups)


@router.post("/login")
async def login(request: Request) -> Response:
    form = await request.form()
    login_csrf_token: str = str(form.get("login_csrf_token", ""))

    if not validate_login_csrf_token(
        cookie_token=request.cookies.get(LOGIN_CSRF_COOKIE),
        form_token=login_csrf_token,
    ):
        return _login_page(
            request=request,
            error_message="درخواست ورود معتبر نیست. صفحه را دوباره بارگذاری کن.",
            status_code=status.HTTP_403_FORBIDDEN,
        )

    username: str = str(form.get("username", ""))
    password: str = str(form.get("password", ""))

    if not validate_password(username=username, password=password):
        return _login_page(
            request=request,
            error_message="نام کاربری یا رمز عبور صحیح نیست",
            status_code=status.HTTP_401_UNAUTHORIZED,
        )

    response: RedirectResponse = RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
    response.set_cookie(
        key=SESSION_COOKIE,
        value=create_session_token(),
        httponly=True,
        secure=COOKIE_SECURE,
        samesite="lax",
        max_age=SESSION_TTL_SECONDS,
    )
    response.delete_cookie(key=LOGIN_CSRF_COOKIE, secure=COOKIE_SECURE, samesite="lax")
    return response


@router.post("/logout")
async def logout(request: Request) -> Response:
    form = await request.form()

    if not _has_valid_csrf(request=request, csrf_token=str(form.get("csrf_token", ""))):
        return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)

    response: RedirectResponse = RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
    response.delete_cookie(key=SESSION_COOKIE, secure=COOKIE_SECURE, samesite="lax")
    return response


@router.post("/backups/{filename}/download")
async def create_download_link(filename: str, request: Request) -> Response:
    if not _is_authenticated(request=request):
        return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)

    form = await request.form()

    if not _has_valid_csrf(request=request, csrf_token=str(form.get("csrf_token", ""))):
        return _dashboard_page(
            request=request,
            backups=list_backups(),
            error_message="درخواست معتبر نیست. صفحه را دوباره بارگذاری کن.",
            status_code=status.HTTP_403_FORBIDDEN,
        )

    totp_code: str = str(form.get("totp", ""))

    if not validate_totp(code=totp_code):
        return _dashboard_page(
            request=request,
            backups=list_backups(),
            error_message="کد TOTP صحیح نیست یا منقضی شده است",
            status_code=status.HTTP_401_UNAUTHORIZED,
        )

    backup_path: Path | None = get_backup_or_none(filename=filename)

    if not backup_path:
        return _dashboard_page(
            request=request,
            backups=list_backups(),
            error_message="فایل بکاپ پیدا نشد",
            status_code=status.HTTP_404_NOT_FOUND,
        )

    token: str = create_download_token(filename=backup_path.name)
    download_url: str = "/backups/{}/download?token={}".format(backup_path.name, token)
    return RedirectResponse(url=download_url, status_code=status.HTTP_303_SEE_OTHER)


@router.get("/backups/{filename}/download")
async def download_backup(filename: str, token: str = "") -> Response:
    if not validate_download_token(token=token, filename=filename):
        return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)

    backup_path: Path | None = get_backup_or_none(filename=filename)

    if not backup_path:
        return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)

    if USE_NGINX_ACCEL:
        return _nginx_download_response(backup_path=backup_path)

    return FileResponse(
        path=backup_path,
        filename=backup_path.name,
        media_type="application/octet-stream",
    )


def _is_authenticated(request: Request) -> bool:
    token: str | None = request.cookies.get(SESSION_COOKIE)
    return validate_session_token(token=token)


def _has_valid_csrf(request: Request, csrf_token: str) -> bool:
    session_token: str | None = request.cookies.get(SESSION_COOKIE)
    return validate_csrf_token(session_token=session_token, csrf_token=csrf_token)


def _nginx_download_response(backup_path: Path) -> Response:
    return Response(
        status_code=status.HTTP_200_OK,
        headers={
            "X-Accel-Redirect": "/_protected_backups/{}".format(quote(backup_path.name)),
            "Content-Disposition": 'attachment; filename="{}"'.format(backup_path.name),
            "Content-Type": "application/octet-stream",
        },
    )


def _login_page(
    request: Request,
    error_message: str = "",
    status_code: int = status.HTTP_200_OK,
) -> HTMLResponse:
    login_csrf_token: str = create_login_csrf_token()
    context: dict[str, Any] = _base_context(request=request)
    context["error_message"] = error_message
    context["login_csrf_token"] = login_csrf_token
    response: HTMLResponse = templates.TemplateResponse("login.html", context, status_code=status_code)
    response.set_cookie(
        key=LOGIN_CSRF_COOKIE,
        value=login_csrf_token,
        httponly=True,
        secure=COOKIE_SECURE,
        samesite="lax",
        max_age=600,
    )
    return response


def _dashboard_page(
    request: Request,
    backups: list[Path],
    error_message: str = "",
    status_code: int = status.HTTP_200_OK,
) -> HTMLResponse:
    context: dict[str, Any] = _base_context(request=request)
    context["error_message"] = error_message
    context["backups"] = [_backup_view(backup=backup) for backup in backups]
    context["total_size"] = _format_size(sum(backup.stat().st_size for backup in backups))
    return templates.TemplateResponse("dashboard.html", context, status_code=status_code)


def _base_context(request: Request) -> dict[str, Any]:
    session_token: str | None = request.cookies.get(SESSION_COOKIE)
    return {
        "request": request,
        "favicon_url": FAVICON_URL,
        "logo_url": LOGO_URL,
        "csrf_token": create_csrf_token(session_token=session_token) if session_token and validate_session_token(session_token) else "",
    }


def _backup_view(backup: Path) -> dict[str, str]:
    return {
        "name": backup.name,
        "size": _format_size(backup.stat().st_size),
        "modified": _format_timestamp(backup.stat().st_mtime),
        "download_url": "/backups/{}/download".format(backup.name),
    }


def _format_size(size: int) -> str:
    value: float = float(size)
    units: list[str] = ["B", "KB", "MB", "GB", "TB"]

    for unit in units:
        if value < 1024 or unit == units[-1]:
            return "{:.2f} {}".format(value, unit)

        value = value / 1024

    return "{} B".format(size)


def _format_timestamp(timestamp: float) -> str:
    from datetime import datetime

    return datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M:%S")
