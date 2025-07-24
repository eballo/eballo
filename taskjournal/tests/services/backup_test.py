import zipfile
from datetime import datetime

import pytest

from taskjournal.services.backup import create_backup


@pytest.fixture
def base_dir(tmp_path, monkeypatch):
    # Create dummy files
    (tmp_path / "note1.txt").write_text("Note 1")
    (tmp_path / "subfolder").mkdir()
    (tmp_path / "subfolder" / "note2.txt").write_text("Note 2")

    # Patch BASE_DIR in utils
    monkeypatch.setattr("taskjournal.services.backup.BASE_DIR", tmp_path)
    return tmp_path


@pytest.fixture
def backup_dir(tmp_path, monkeypatch):
    backup_path = tmp_path / "backups"
    monkeypatch.setenv("BACKUP_DIR", str(backup_path))
    monkeypatch.setattr("taskjournal.services.backup.BACKUP_DIR", backup_path)
    return backup_path


def test_create_backup_given_files_exist_when_backup_called_then_zip_created(
    base_dir, backup_dir
):
    # given
    expected_filename = f"DailyNotes_backup_{datetime.now().strftime('%Y_%m_%d')}.zip"

    # when
    backup_file = create_backup()

    # then
    assert backup_file.name == expected_filename
    assert backup_file.exists()

    with zipfile.ZipFile(backup_file, "r") as zipf:
        files = zipf.namelist()
        assert "note1.txt" in files
        assert "subfolder/note2.txt" in files
