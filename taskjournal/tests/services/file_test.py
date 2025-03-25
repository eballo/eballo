import os
from datetime import datetime
from services.file import get_week_folder
from unittest.mock import patch


@patch("taskjournal.commands.datetime")
def test_get_week_folder(mock_datetime, base_dir):
    # Given
    mock_datetime.now.return_value = datetime(2025, 1, 19)
    date = mock_datetime.now()
    expected_folder = os.path.join(base_dir, "2025", "week3")
    # Then / When
    assert get_week_folder(base_dir, date) == expected_folder
