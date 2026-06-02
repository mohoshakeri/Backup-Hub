from dataclasses import dataclass
from pathlib import Path
from typing import Protocol


@dataclass(frozen=True)
class BackupContext:
    name: str
    root_dir: Path
    tmp_dir: Path


class DatabaseBackupProvider(Protocol):
    name: str

    def is_configured(self) -> bool:
        # Return True When Env Has Enough Information
        ...

    def backup(self, context: BackupContext) -> list[Path]:
        # Write Backup Files And Return Created Paths
        ...
