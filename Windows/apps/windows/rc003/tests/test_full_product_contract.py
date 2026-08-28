import unittest
from pathlib import Path

from ovb_rc003 import config


ROOT = Path(__file__).resolve().parents[1]


class FullProductContractTests(unittest.TestCase):
    def test_raw_audio_archive_is_privacy_safe_by_default(self):
        self.assertFalse(config.default_config()["retain_voice_audio"])

    def test_mapping_page_contains_compact_live_voice_meter(self):
        qml = (ROOT / "src" / "ovb_rc003" / "qml" / "ButtonsPage.qml").read_text(
            encoding="utf-8"
        )
        self.assertIn('objectName: "voiceLevelCapsule"', qml)
        self.assertIn("SettingsController.voiceLevel", qml)
        self.assertIn("SettingsController.voiceActive", qml)

    def test_statistics_page_exposes_opt_in_four_hour_archive(self):
        qml = (ROOT / "src" / "ovb_rc003" / "qml" / "StatisticsPage.qml").read_text(
            encoding="utf-8"
        )
        self.assertIn('objectName: "voiceArchiveSwitch"', qml)
        self.assertIn("4 小时", qml)
        self.assertIn("SettingsController.voiceArchiveSessions", qml)


if __name__ == "__main__":
    unittest.main()
