"""Convert decoded RC003 PCM into a compact UI loudness value.

The bridge receives 16 kHz mono signed-16-bit samples.  This module keeps only
one 50 ms RMS window and never retains voice content.  The output is normalized
to ``0.0 ... 1.0`` and smoothed with a faster attack than release so the tiny
status meter remains responsive without flickering.
"""

from __future__ import annotations

import math
from typing import Iterable, Optional


class VoiceAudioLevelMeter:
    SAMPLE_RATE_HZ = 16_000
    UPDATE_WINDOW_SAMPLES = SAMPLE_RATE_HZ // 20
    NOISE_FLOOR_DBFS = -60.0
    DISPLAY_CEILING_DBFS = -6.0
    ATTACK_COEFFICIENT = 0.72
    RELEASE_COEFFICIENT = 0.28

    def __init__(self) -> None:
        self._square_sum = 0.0
        self._sample_count = 0
        self._level = 0.0

    @property
    def level(self) -> float:
        return self._level

    def append(self, samples: Iterable[int]) -> Optional[float]:
        """Return the latest completed display window, if one completed."""

        latest = None
        for sample in samples:
            normalized = float(sample) / 32_768.0
            self._square_sum += normalized * normalized
            self._sample_count += 1
            if self._sample_count != self.UPDATE_WINDOW_SAMPLES:
                continue

            rms = math.sqrt(self._square_sum / self._sample_count)
            target = self.normalized_level(rms)
            coefficient = (
                self.ATTACK_COEFFICIENT
                if target >= self._level
                else self.RELEASE_COEFFICIENT
            )
            self._level += (target - self._level) * coefficient
            latest = self._level
            self._square_sum = 0.0
            self._sample_count = 0
        return latest

    def reset(self) -> None:
        self._square_sum = 0.0
        self._sample_count = 0
        self._level = 0.0

    @classmethod
    def normalized_level(cls, rms: float) -> float:
        if not math.isfinite(rms) or rms <= 0:
            return 0.0
        decibels = 20.0 * math.log10(min(1.0, rms))
        normalized = (decibels - cls.NOISE_FLOOR_DBFS) / (
            cls.DISPLAY_CEILING_DBFS - cls.NOISE_FLOOR_DBFS
        )
        return min(1.0, max(0.0, normalized))
