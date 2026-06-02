from utils.config import BACKUP_CRON


def main() -> None:
    print(f"{BACKUP_CRON} python -m tasks.backup")


if __name__ == "__main__":
    main()
