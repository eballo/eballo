from datetime import datetime

from taskjournal.services.backup import BackupService
from taskjournal.services.logger import logger
from taskjournal.services.time import TimeService


class AdminCommands:

    def __init__(self, backup_service: BackupService, time_service: TimeService) -> None:
        self.backup_service = backup_service
        self.time_service = time_service

    def create_backup(self) -> None:
        backup_file = self.backup_service.create()
        logger.info(f"Backup created at: {backup_file}")

    def show_info(self, today: datetime) -> None:
        day_name = today.strftime("%A")
        week_number = today.isocalendar()[1]
        logger.info(f"📅 Today is {day_name}, {today.strftime('%Y-%m-%d')}")
        logger.info(f"🔢 We are in week {week_number}")
