import math
import unittest

from ovb_rc003.voice_audio_level import VoiceAudioLevelMeter


class VoiceAudioLevelMeterTests(unittest.TestCase):
    def test_silence_produces_zero_after_one_window(self):
        meter = VoiceAudioLevelMeter()
        self.assertEqual(meter.append([0] * meter.UPDATE_WINDOW_SAMPLES), 0.0)

    def test_partial_window_does_not_publish(self):
        meter = VoiceAudioLevelMeter()
        self.assertIsNone(meter.append([1000] * (meter.UPDATE_WINDOW_SAMPLES - 1)))
        self.assertIsNotNone(meter.append([1000]))

    def test_louder_pcm_produces_a_higher_display_level(self):
        quiet = VoiceAudioLevelMeter()
        loud = VoiceAudioLevelMeter()
        quiet_level = quiet.append([200] * quiet.UPDATE_WINDOW_SAMPLES)
        loud_level = loud.append([12_000] * loud.UPDATE_WINDOW_SAMPLES)
        self.assertIsNotNone(quiet_level)
        self.assertIsNotNone(loud_level)
        self.assertGreater(loud_level, quiet_level)

    def test_attack_is_faster_than_release(self):
        meter = VoiceAudioLevelMeter()
        peak = meter.append([20_000] * meter.UPDATE_WINDOW_SAMPLES)
        released = meter.append([0] * meter.UPDATE_WINDOW_SAMPLES)
        self.assertGreater(peak, 0.0)
        self.assertGreater(released, 0.0)
        self.assertLess(released, peak)

    def test_normalization_clamps_invalid_and_extreme_values(self):
        self.assertEqual(VoiceAudioLevelMeter.normalized_level(0), 0.0)
        self.assertEqual(VoiceAudioLevelMeter.normalized_level(float("nan")), 0.0)
        self.assertEqual(VoiceAudioLevelMeter.normalized_level(float("inf")), 0.0)
        self.assertEqual(VoiceAudioLevelMeter.normalized_level(10), 1.0)
        self.assertTrue(
            math.isclose(VoiceAudioLevelMeter.normalized_level(10 ** (-60 / 20)), 0.0)
        )

    def test_reset_discards_partial_window_and_smoothed_level(self):
        meter = VoiceAudioLevelMeter()
        meter.append([10_000] * meter.UPDATE_WINDOW_SAMPLES)
        meter.append([10_000] * 100)
        meter.reset()
        self.assertEqual(meter.level, 0.0)
        self.assertIsNone(meter.append([10_000] * 700))
