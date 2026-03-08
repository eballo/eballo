from datetime import datetime
from zipfile import ZipFile

from pytest import mark

from taskjournal.services.backup import create_backup


@mark.usefixtures("backup_source_dir", "backup_output_dir")
class TestBackup:

    def test_create_backup_given_files_exist_when_backup_called_then_zip_created(
        self,
    ) -> None:
        # given
        expected_filename = (
            f"DailyNotes_backup_{datetime.now().strftime('%Y_%m_%d')}.zip"
        )

        # when
        backup_file = create_backup()

        # then
        assert backup_file.name == expected_filename
        assert backup_file.exists()

        with ZipFile(backup_file, "r") as zipf:
            files = zipf.namelist()
            assert "note1.txt" in files
            assert "subfolder/note2.txt" in files
