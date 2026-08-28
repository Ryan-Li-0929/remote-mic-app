"""Small cross-process runtime status channel for the Windows settings UI.

The bridge and settings window are separate processes.  On Windows they open
the same named memory mapping and exchange only an active flag, a normalized
audio level, and a timestamp.  No PCM, transcript, device path, or Bluetooth
identity crosses this boundary.
"""

from __future__ import annotations

import mmap
import struct
import sys
import threading
import time
from dataclasses import dataclass
from typing import Callable, Optional


MAPPING_NAME = "Local\\SayAll.RC003.RuntimeStatus.v1"
_MAGIC = b"SA03"
_VERSION = 1
_STATUS = struct.Struct("<4sIIB3xfQI")
STATUS_SIZE = _STATUS.size


@dataclass(frozen=True)
class VoiceRuntimeStatus:
    level: float = 0.0
    active: bool = False
    updated_at_ns: int = 0
    fresh: bool = False


class RuntimeStatusChannel:
    """Read/write one seqlock-style status record.

    ``buffer`` is injectable for deterministic tests.  Production Windows
    callers omit it and receive the process-shared named mapping.
    """

    def __init__(
        self,
        *,
        buffer=None,
        clock_ns: Callable[[], int] = time.time_ns,
    ) -> None:
        self._clock_ns = clock_ns
        self._owns_buffer = buffer is None
        self._buffer = buffer if buffer is not None else self._open_mapping()
        self._sequence = 0
        self._lock = threading.Lock()

    @staticmethod
    def _open_mapping():
        if sys.platform == "win32":
            return mmap.mmap(-1, STATUS_SIZE, tagname=MAPPING_NAME, access=mmap.ACCESS_WRITE)
        # The application is Windows-only.  A private map keeps imports and
        # hardware-free tests usable on other hosts without pretending to
        # provide cross-process transport there.
        return mmap.mmap(-1, STATUS_SIZE)

    def publish(self, level: float, active: bool) -> None:
        level = min(1.0, max(0.0, float(level)))
        self._sequence = (self._sequence + 2) & 0xFFFFFFFE
        if self._sequence == 0:
            self._sequence = 2
        payload = _STATUS.pack(
            _MAGIC,
            _VERSION,
            self._sequence,
            bool(active),
            level,
            int(self._clock_ns()),
            self._sequence,
        )
        with self._lock:
            self._buffer.seek(0)
            self._buffer.write(payload)

    def reset(self) -> None:
        self.publish(0.0, False)

    def read(self, *, max_age_seconds: float = 1.0) -> VoiceRuntimeStatus:
        for _ in range(3):
            first = self._snapshot()
            second = self._snapshot()
            if first == second:
                parsed = self._parse(first)
                if parsed is not None:
                    level, active, updated_at_ns = parsed
                    age_ns = max(0, int(self._clock_ns()) - updated_at_ns)
                    fresh = age_ns <= int(max_age_seconds * 1_000_000_000)
                    if fresh:
                        return VoiceRuntimeStatus(level, active, updated_at_ns, True)
                    return VoiceRuntimeStatus(updated_at_ns=updated_at_ns)
        return VoiceRuntimeStatus()

    def _snapshot(self) -> bytes:
        with self._lock:
            self._buffer.seek(0)
            return self._buffer.read(STATUS_SIZE)

    @staticmethod
    def _parse(payload: bytes) -> Optional[tuple[float, bool, int]]:
        if len(payload) != STATUS_SIZE:
            return None
        magic, version, sequence, active, level, updated_at_ns, sequence_end = (
            _STATUS.unpack(payload)
        )
        if (
            magic != _MAGIC
            or version != _VERSION
            or sequence == 0
            or sequence != sequence_end
        ):
            return None
        return min(1.0, max(0.0, float(level))), bool(active), int(updated_at_ns)

    def close(self) -> None:
        if self._owns_buffer:
            with self._lock:
                self._buffer.close()

    def __enter__(self):
        return self

    def __exit__(self, _type, _value, _traceback) -> None:
        self.close()
