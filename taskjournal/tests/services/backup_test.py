from pathlib import Path
from zipfile import ZIP_DEFLATED, BadZipFile, ZipFile

import pytest

from freezegun import freeze_time

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

        result = BackupService(
            backup_dir=str(backup_dir), base_dir=str(base_dir)
        ).health_check()

        assert result.status == ServiceStatus.OK

    def test_health_check_warning_when_base_dir_missing(self, tmp_path: Path) -> None:
        backup_dir = tmp_path / "backup"
        backup_dir.mkdir()

        result = BackupService(
            backup_dir=str(backup_dir), base_dir="/nonexistent"
        ).health_check()

        assert result.status == ServiceStatus.WARNING
        assert any("BASE_DIR" in d for d in result.details)

    def test_health_check_warning_when_backup_dir_missing(self, tmp_path: Path) -> None:
        base_dir = tmp_path / "notes"
        base_dir.mkdir()

        result = BackupService(
            backup_dir="/nonexistent", base_dir=str(base_dir)
        ).health_check()

        assert result.status == ServiceStatus.WARNING
        assert any("BACKUP_DIR" in d for d in result.details)

    def test_health_check_warning_when_both_dirs_missing(self) -> None:
        result = BackupService(
            backup_dir="/nobackup", base_dir="/nobase"
        ).health_check()

        assert result.status == ServiceStatus.WARNING
        assert len(result.details) == 2

    def test_accepts_path_objects_from_config(self, tmp_path: Path) -> None:
        backup_dir = tmp_path / "backup"
        base_dir = tmp_path / "notes"
        backup_dir.mkdir()
        base_dir.mkdir()

        svc = BackupService(backup_dir=backup_dir, base_dir=base_dir)

        assert svc.health_check().status == ServiceStatus.OK

    @freeze_time("2026-07-22 10:51:28")
    def test_create_backup_given_files_exist_when_backup_called_then_zip_created(
        self,
        backup_service_instance: BackupService,
    ) -> None:
        # given
        expected_filename = "DailyNotes_backup_2026_07_22_10_51_28.zip"

        # when
        backup_file = backup_service_instance.create()

        # then
        assert backup_file.name == expected_filename
        assert backup_file.exists()

        with ZipFile(backup_file, "r") as zipf:
            files = zipf.namelist()
            assert "note1.txt" in files
            assert "subfolder/note2.txt" in files

    def test_inspect_and_restore_preserve_existing_notes(self, tmp_path: Path) -> None:
        notes = tmp_path / "notes"
        notes.mkdir()
        (notes / "old.txt").write_text("original")
        svc = BackupService(tmp_path / "backups", notes)
        archive = svc.create()
        (notes / "old.txt").write_text("newer")
        with ZipFile(archive, "a") as zipf:
            zipf.writestr("nested/missing.md", "restored")

        assert svc.inspect(archive) == [
            (Path("old.txt"), True),
            (Path("nested/missing.md"), False),
        ]
        assert svc.restore(archive) == [Path("nested/missing.md")]
        assert (notes / "old.txt").read_text() == "newer"
        assert (notes / "nested/missing.md").read_text() == "restored"
        assert svc.restore(archive) == []

    @pytest.mark.parametrize(
        "member", ["../escape.md", "/absolute.md", "C:/outside.md", "..\\escape.md"]
    )
    def test_unsafe_archive_is_rejected_before_writing(
        self, tmp_path: Path, member: str
    ) -> None:
        notes = tmp_path / "notes"
        archive = tmp_path / "bad.zip"
        with ZipFile(archive, "w", ZIP_DEFLATED) as zipf:
            zipf.writestr("safe.md", "safe")
            zipf.writestr(member, "unsafe")
        svc = BackupService(tmp_path, notes)

        with pytest.raises(ValueError, match="Unsafe backup entry"):
            svc.restore(archive)
        assert not notes.exists()
        assert not (tmp_path / "escape.md").exists()

    def test_restore_rejects_symlinked_parent(self, tmp_path: Path) -> None:
        notes = tmp_path / "notes"
        outside = tmp_path / "outside"
        notes.mkdir()
        outside.mkdir()
        (notes / "nested").symlink_to(outside, target_is_directory=True)
        archive = tmp_path / "bad.zip"
        with ZipFile(archive, "w") as zipf:
            zipf.writestr("nested/escape.md", "unsafe")

        with pytest.raises(ValueError, match="Unsafe backup entry"):
            BackupService(tmp_path, notes).restore(archive)
        assert not (outside / "escape.md").exists()

    def test_corrupt_backup_fails_integrity_check(self, tmp_path: Path) -> None:
        archive = tmp_path / "bad.zip"
        archive.write_text("not a zip")
        with pytest.raises(BadZipFile):
            BackupService(tmp_path, tmp_path / "notes").inspect(archive)
