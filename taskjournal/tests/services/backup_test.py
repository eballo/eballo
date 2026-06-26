from datetime import datetime
from pathlib import Path
from zipfile import ZipFile

from taskjournal.services.backup import BackupService
from taskjournal.services.base import ServiceStatus


class TestBackup:

    def test_name_property(self) -> None:
        svc = BackupService(backup_dir="/b", base_dir="/s")
        assert svc.name == "Backup"

    def test_health_check_ok_when_both_dirs_exist(self, tmp_path: Path) -> None:
        backup_dir = tmp_path / "backup"
        base_dir = tmp_path / "notes"
        backup_dir.mkdir()
        base_dir.mkdir()

        result = BackupService(backup_dir=str(backup_dir), base_dir=str(base_dir)).health_check()

        assert result.status == ServiceStatus.OK

    def test_health_check_warning_when_base_dir_missing(self, tmp_path: Path) -> None:
        backup_dir = tmp_path / "backup"
        backup_dir.mkdir()

        result = BackupService(backup_dir=str(backup_dir), base_dir="/nonexistent").health_check()

        assert result.status == ServiceStatus.WARNING
        assert any("BASE_DIR" in d for d in result.details)

    def test_health_check_warning_when_backup_dir_missing(self, tmp_path: Path) -> None:
        base_dir = tmp_path / "notes"
        base_dir.mkdir()

        result = BackupService(backup_dir="/nonexistent", base_dir=str(base_dir)).health_check()

        assert result.status == ServiceStatus.WARNING
        assert any("BACKUP_DIR" in d for d in result.details)

    def test_health_check_warning_when_both_dirs_missing(self) -> None:
        result = BackupService(backup_dir="/nobackup", base_dir="/nobase").health_check()

        assert result.status == ServiceStatus.WARNING
        assert len(result.details) == 2

    def test_accepts_path_objects_from_config(self, tmp_path: Path) -> None:
        backup_dir = tmp_path / "backup"
        base_dir = tmp_path / "notes"
        backup_dir.mkdir()
        base_dir.mkdir()

        svc = BackupService(backup_dir=backup_dir, base_dir=base_dir)

        assert svc.health_check().status == ServiceStatus.OK

    def test_create_backup_given_files_exist_when_backup_called_then_zip_created(
        self,
        backup_service_instance: BackupService,
    ) -> None:
        # given
        expected_filename = (
            f"DailyNotes_backup_{datetime.now().strftime('%Y_%m_%d')}.zip"
        )

        # when
        backup_file = backup_service_instance.create()

        # then
        assert backup_file.name == expected_filename
        assert backup_file.exists()

        with ZipFile(backup_file, "r") as zipf:
            files = zipf.namelist()
            assert "note1.txt" in files
            assert "subfolder/note2.txt" in files
