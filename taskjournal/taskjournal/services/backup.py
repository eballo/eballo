import os
import zipfile
from datetime import datetime
from pathlib import Path

from taskjournal.config import BACKUP_DIR, BASE_DIR


def _get_backup_filename():
    date_str = datetime.now().strftime("%Y_%m_%d")
    return f"DailyNotes_backup_{date_str}.zip"


def create_backup():
    Path(BACKUP_DIR).mkdir(parents=True, exist_ok=True)
    backup_file = BACKUP_DIR / _get_backup_filename()

    with zipfile.ZipFile(backup_file, "w", zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(BASE_DIR):
            for file in files:
                full_path = Path(root) / file
                relative_path = full_path.relative_to(BASE_DIR)
                zipf.write(full_path, arcname=relative_path)

    return backup_file
