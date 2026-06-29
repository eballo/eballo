from datetime import datetime
from os import walk
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

from taskjournal.services.base import BaseService, HealthCheckResult, ServiceStatus
from taskjournal.services.logger import logger


class BackupService(BaseService):

    @property
    def name(self) -> str:
        return "Backup"

    def health_check(self) -> HealthCheckResult:
        details = []
        if not Path(str(self.base_dir)).exists():
            details.append(f"BASE_DIR not found: {self.base_dir}")
        if not Path(str(self.backup_dir)).exists():
            details.append(f"BACKUP_DIR not found: {self.backup_dir}")
        if details:
            return HealthCheckResult(
                ServiceStatus.WARNING,
                "One or more directories missing (will be created on first run)",
                details,
            )
        return HealthCheckResult(
            ServiceStatus.OK,
            f"Directories OK (backup: {self.backup_dir})",
        )

    def __init__(self, backup_dir: str | Path, base_dir: str | Path) -> None:
        self.backup_dir = backup_dir
        self.base_dir = base_dir

    @staticmethod
    def _get_backup_filename() -> str:
        date_str = datetime.now().strftime("%Y_%m_%d")
        return f"DailyNotes_backup_{date_str}.zip"

    def create(self) -> Path:
        Path(self.backup_dir).mkdir(parents=True, exist_ok=True)
        backup_file = Path(self.backup_dir) / BackupService._get_backup_filename()
        logger.info(f"Creating backup at {backup_file}...")

        with ZipFile(backup_file, "w", ZIP_DEFLATED) as zipf:
            for root, _dirs, files in walk(self.base_dir):
                for file in files:
                    full_path = Path(root) / file
                    relative_path = full_path.relative_to(self.base_dir)
                    zipf.write(full_path, arcname=relative_path)

        logger.debug(f"Backup complete: {backup_file}")
        return backup_file
