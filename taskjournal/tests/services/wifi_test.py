import unittest
from unittest.mock import patch, MagicMock

from taskjournal.services.wifi import WifiService


class TestWifiService(unittest.TestCase):
    def setUp(self):
        self.wifi_service = WifiService()

    @patch("taskjournal.services.wifi.subprocess.run")
    def test_get_name_success(self, mock_run):
        """Test getting WiFi name successfully"""
        mock_result = MagicMock()
        mock_result.stdout = "Preferred networks on en0:\n\tCodePI\n\tTSH\n"
        mock_run.return_value = mock_result

        result = self.wifi_service.get_name()

        self.assertEqual(result, "CodePI")
        mock_run.assert_called_once_with(
            ["networksetup", "-listpreferredwirelessnetworks", "en0"],
            capture_output=True,
            text=True,
            check=True,
        )

    @patch("taskjournal.services.wifi.subprocess.run")
    def test_get_name_no_networks(self, mock_run):
        """Test when no preferred networks are configured"""
        mock_result = MagicMock()
        mock_result.stdout = "Preferred networks on en0:\n"
        mock_run.return_value = mock_result

        result = self.wifi_service.get_name()

        self.assertIsNone(result)

    @patch("taskjournal.services.wifi.subprocess.run")
    def test_get_name_exception(self, mock_run):
        """Test when an exception occurs"""
        mock_run.side_effect = Exception("Network error")

        result = self.wifi_service.get_name()

        self.assertIsNone(result)
