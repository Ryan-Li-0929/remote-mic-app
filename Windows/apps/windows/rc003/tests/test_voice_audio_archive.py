import os
import tempfile
import unittest
import wave
from datetime import datetime
from pathlib import Path

from ovb_rc003.voice_audio_archive import (
    RETENTION_SECONDS,
    VoiceAudioArchive,
    archive_root,
    list_sessions,
    prune_expired,
)


class VoiceAudioArchiveTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name) / "voice-audio"
        self.now = 1_800_000_000.0

    def tearDown(self):
        self.temp.cleanup()

    def test_disabled_archive_never_creates_directory(self):
        archive = VoiceAudioArchive(self.root, enabled=False, clock=lambda: self.now)
        self.assertFalse(archive.start("42"))
        archive.append([1, 2, 3])
        archive.stop()
        archive.close()
        self.assertFalse(self.root.exists())

    def test_session_writes_valid_mono_16khz_wav_and_four_hour_expiry(self):
        archive = VoiceAudioArchive(self.root, enabled=True, clock=lambda: self.now)
        self.assertTrue(archive.start("42"))
        archive.append([1000] * 1600)
        self.now += 0.1
        archive.stop()
        archive.close()

        sessions = list_sessions(self.root, now=lambda: self.now)
        self.assertEqual(len(sessions), 1)
        session = sessions[0]
        self.assertAlmostEqual(session["duration_seconds"], 0.1, places=3)
        expires = datetime.fromisoformat(session["expires_at"]).timestamp()
        ended = datetime.fromisoformat(session["ended_at"]).timestamp()
        self.assertEqual(expires - ended, RETENTION_SECONDS)
        with wave.open(session["audio_path"], "rb") as audio:
            self.assertEqual(audio.getnchannels(), 1)
            self.assertEqual(audio.getsampwidth(), 2)
            self.assertEqual(audio.getframerate(), 16_000)
            self.assertEqual(audio.getnframes(), 1600)

    def test_prune_removes_audio_and_metadata_at_expiry(self):
        archive = VoiceAudioArchive(self.root, enabled=True, clock=lambda: self.now)
        archive.start("expire")
        archive.append([10] * 800)
        archive.stop()
        archive.close()
        self.assertEqual(len(list_sessions(self.root, now=lambda: self.now)), 1)

        self.now += RETENTION_SECONDS
        prune_expired(self.root, now=lambda: self.now)
        self.assertEqual(list(self.root.glob("*")), [])

    def test_archive_root_is_scoped_below_config_root(self):
        config_root = Path(self.temp.name) / "RemoteMic" / "RC003"
        self.assertEqual(archive_root(config_root), config_root / "voice-audio")

    def test_corrupt_metadata_cannot_keep_audio_past_four_hours(self):
        self.root.mkdir(parents=True)
        audio = self.root / "orphan.wav"
        metadata = self.root / "orphan.json"
        audio.write_bytes(b"not important")
        metadata.write_text("{broken", encoding="utf-8")
        old = self.now - RETENTION_SECONDS
        os.utime(audio, (old, old))
        os.utime(metadata, (old, old))
        prune_expired(self.root, now=lambda: self.now)
        self.assertFalse(audio.exists())
        self.assertFalse(metadata.exists())


if __name__ == "__main__":
    unittest.main()
