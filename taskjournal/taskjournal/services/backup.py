from datetime import datetime
from os import walk
from pathlib import Path
from shutil import copyfileobj
from stat import S_IFMT, S_IFLNK
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

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
        date_str = datetime.now().strftime("%Y_%m_%d_%H_%M_%S")
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

    def _entries(self, archive: ZipFile) -> list[tuple[ZipInfo, Path]]:
        root = Path(self.base_dir).resolve()
        entries = []
        seen: set[Path] = set()
        for info in archive.infolist():
            name = info.filename
            parts = name.rstrip("/").split("/")
            relative = Path(*parts)
            target = root / relative
            if (
                not name
                or name.startswith("/")
                or "\\" in name
                or any(part in ("", ".", "..") for part in parts)
                or ":" in parts[0]
                or "\x00" in name
                or S_IFMT(info.external_attr >> 16) == S_IFLNK
                or not target.resolve().is_relative_to(root)
                or any(
                    (root / Path(*parts[:i])).is_symlink()
                    for i in range(1, len(parts) + 1)
                )
                or relative in seen
            ):
                raise ValueError(f"Unsafe backup entry: {name}")
            seen.add(relative)
            if not info.is_dir():
                entries.append((info, relative))
        return entries

    def inspect(self, backup_file: str | Path) -> list[tuple[Path, bool]]:
        """Validate archive integrity and preview files already present in BASE_DIR."""
        with ZipFile(backup_file) as archive:
            entries = self._entries(archive)
            bad = archive.testzip()
            if bad is not None:
                raise ValueError(f"Corrupt backup entry: {bad}")
            root = Path(self.base_dir)
            return [
                (relative, (root / relative).exists() or (root / relative).is_symlink())
                for _, relative in entries
            ]

    def restore(self, backup_file: str | Path) -> list[Path]:
        """Restore missing files only; never overwrite a current note."""
        self.inspect(backup_file)
        root = Path(self.base_dir)
        restored = []
        with ZipFile(backup_file) as archive:
            entries = self._entries(archive)
            for info, relative in entries:
                target = root / relative
                if target.exists() or target.is_symlink():
                    continue
                target.parent.mkdir(parents=True, exist_ok=True)
                # Recheck after creating directories to avoid following a new symlink.
                if not target.resolve().is_relative_to(root.resolve()):
                    raise ValueError(f"Unsafe backup entry: {info.filename}")
                try:
                    with archive.open(info) as source, target.open("xb") as destination:
                        copyfileobj(source, destination)
                except FileExistsError:
                    continue
                restored.append(relative)
        return restored
