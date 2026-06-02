from pathlib import Path
from typing import Any

from fastapi import APIRouter, Request, Response, status
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from services.auth import create_session_token, validate_password, validate_session_token, validate_totp
from services.backups import get_backup_or_none, list_backups
from services.download_tokens import create_download_token, validate_download_token
from utils.config import COOKIE_SECURE, FAVICON_URL, LOGO_URL, PROJECT_ROOT, SESSION_COOKIE

router: APIRouter = APIRouter(tags=["Web"])
templates: Jinja2Templates = Jinja2Templates(directory=str(PROJECT_ROOT / "templates"))


@router.get("/", response_class=HTMLResponse)
async def index(request: Request) -> HTMLResponse:
    if not _is_authenticated(request=request):
        return _login_page(request=request)

    backups: list[Path] = list_backups()
    return _dashboard_page(request=request, backups=backups)


@router.post("/login")
async def login(request: Request) -> Response:
    form = await request.form()
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
    )
    return response


@router.post("/logout")
async def logout() -> Response:
    response: RedirectResponse = RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
    response.delete_cookie(key=SESSION_COOKIE)
    return response


@router.post("/backups/{filename}/download")
async def create_download_link(filename: str, request: Request) -> Response:
    if not _is_authenticated(request=request):
        return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)

    form = await request.form()
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

    return FileResponse(
        path=backup_path,
        filename=backup_path.name,
        media_type="application/octet-stream",
    )


def _is_authenticated(request: Request) -> bool:
    token: str | None = request.cookies.get(SESSION_COOKIE)
    return validate_session_token(token=token)


def _login_page(
    request: Request,
    error_message: str = "",
    status_code: int = status.HTTP_200_OK,
) -> HTMLResponse:
    context: dict[str, Any] = _base_context(request=request)
    context["error_message"] = error_message
    return templates.TemplateResponse("login.html", context, status_code=status_code)


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
    return {
        "request": request,
        "favicon_url": FAVICON_URL,
        "logo_url": LOGO_URL,
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
