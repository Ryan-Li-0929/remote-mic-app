"""Privacy-bounded temporary archive of decoded RC003 microphone audio."""

from __future__ import annotations

import json
import os
import queue
import threading
import time
import wave
from array import array
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Iterable, Optional


RETENTION_SECONDS = 4 * 60 * 60
SAMPLE_RATE_HZ = 16_000
MAX_PENDING_CHUNKS = 256


@dataclass(frozen=True)
class ArchivedVoiceSession:
    session_id: str
    started_at: str
    ended_at: str
    expires_at: str
    duration_seconds: float
    audio_path: str
    dropped_chunks: int = 0


def _iso_utc(timestamp: float) -> str:
    return datetime.fromtimestamp(timestamp, timezone.utc).isoformat()


def archive_root(config_root: Path) -> Path:
    return config_root / "voice-audio"


def list_sessions(root: Path, *, now: Callable[[], float] = time.time) -> list[dict]:
    prune_expired(root, now=now)
    sessions = []
    for metadata_path in sorted(root.glob("*.json"), reverse=True):
        try:
            record = json.loads(metadata_path.read_text(encoding="utf-8"))
            audio_path = root / str(record["audio_path"])
            if audio_path.is_file():
                record["audio_path"] = str(audio_path)
                sessions.append(record)
        except (OSError, ValueError, KeyError, TypeError):
            continue
    return sessions


def prune_expired(root: Path, *, now: Callable[[], float] = time.time) -> None:
    if not root.exists():
        return
    cutoff = now()
    for metadata_path in root.glob("*.json"):
        try:
            record = json.loads(metadata_path.read_text(encoding="utf-8"))
            expires = datetime.fromisoformat(str(record["expires_at"])).timestamp()
        except (OSError, ValueError, KeyError, TypeError):
            continue
        if expires > cutoff:
            continue
        audio_name = str(record.get("audio_path", ""))
        if audio_name and Path(audio_name).name == audio_name:
            (root / audio_name).unlink(missing_ok=True)
        metadata_path.unlink(missing_ok=True)
    # The filesystem timestamp is the final fail-safe: corrupt/missing
    # metadata must never turn a four-hour archive into indefinite storage.
    for pattern in ("*.wav", "*.json", "*.json.tmp"):
        for candidate in root.glob(pattern):
            try:
                if candidate.stat().st_mtime <= cutoff - RETENTION_SECONDS:
                    candidate.unlink(missing_ok=True)
            except OSError:
                pass


class VoiceAudioArchive:
    """Non-blocking producer with one owned WAV-writer thread."""

    def __init__(
        self,
        root: Path,
        *,
        enabled: bool,
        clock: Callable[[], float] = time.time,
    ) -> None:
        self._root = root
        self._enabled = bool(enabled)
        self._clock = clock
        self._commands: "queue.Queue[tuple]" = queue.Queue(MAX_PENDING_CHUNKS)
        self._thread: Optional[threading.Thread] = None
        self._dropped_chunks = 0

    def start(self, session_id: str) -> bool:
        if not self._enabled:
            return False
        self._ensure_thread()
        return self._put(("start", str(session_id), self._clock()), force=True)

    def append(self, samples: Iterable[int]) -> None:
        if not self._enabled or self._thread is None:
            return
        pcm = array("h", (max(-32768, min(32767, int(value))) for value in samples))
        self._put(("pcm", pcm.tobytes()))

    def stop(self) -> None:
        if self._thread is not None:
            self._put(("stop", self._clock()), force=True)

    def close(self, timeout: float = 2.0) -> None:
        thread = self._thread
        if thread is None:
            return
        if not self._put(("shutdown", self._clock()), force=True):
            raise RuntimeError("voice audio archive queue did not accept shutdown")
        thread.join(timeout=timeout)
        if thread.is_alive():
            raise RuntimeError("voice audio archive writer did not stop")
        self._thread = None

    def _ensure_thread(self) -> None:
        if self._thread is not None and self._thread.is_alive():
            return
        self._root.mkdir(parents=True, exist_ok=True)
        prune_expired(self._root, now=self._clock)
        self._thread = threading.Thread(
            target=self._run,
            name="RC003VoiceAudioArchive",
            daemon=True,
        )
        self._thread.start()

    def _put(self, command: tuple, *, force: bool = False) -> bool:
        try:
            if force:
                self._commands.put(command, timeout=0.5)
            else:
                self._commands.put_nowait(command)
            return True
        except queue.Full:
            self._dropped_chunks += 1
            return False

    def _run(self) -> None:
        writer = None
        partial_path = None
        session_id = ""
        started_at = 0.0
        frames = 0

        def finish(ended_at: float) -> None:
            nonlocal writer, partial_path, session_id, started_at, frames
            if writer is None or partial_path is None:
                return
            writer.close()
            writer = None
            final_path = partial_path.with_name(partial_path.name.replace(".partial.wav", ".wav"))
            partial_path.replace(final_path)
            record = ArchivedVoiceSession(
                session_id=session_id,
                started_at=_iso_utc(started_at),
                ended_at=_iso_utc(ended_at),
                expires_at=_iso_utc(ended_at + RETENTION_SECONDS),
                duration_seconds=frames / SAMPLE_RATE_HZ,
                audio_path=final_path.name,
                dropped_chunks=self._dropped_chunks,
            )
            metadata_path = final_path.with_suffix(".json")
            temporary = metadata_path.with_suffix(".json.tmp")
            temporary.write_text(
                json.dumps(asdict(record), ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            temporary.replace(metadata_path)
            # Keep the filesystem fallback on the same clock as the explicit
            # expiry metadata (also makes deterministic tests independent of
            # the host wall clock).
            os.utime(final_path, (ended_at, ended_at))
            os.utime(metadata_path, (ended_at, ended_at))
            partial_path = None
            session_id = ""
            started_at = 0.0
            frames = 0
            self._dropped_chunks = 0
            prune_expired(self._root, now=self._clock)

        try:
            while True:
                command = self._commands.get()
                kind = command[0]
                if kind == "start":
                    finish(command[2])
                    session_id = command[1]
                    started_at = command[2]
                    safe_id = "".join(c for c in session_id if c.isalnum() or c in "-_")[:64]
                    stamp = int(started_at * 1000)
                    partial_path = self._root / f"{stamp}-{safe_id or 'voice'}.partial.wav"
                    writer = wave.open(str(partial_path), "wb")
                    writer.setnchannels(1)
                    writer.setsampwidth(2)
                    writer.setframerate(SAMPLE_RATE_HZ)
                elif kind == "pcm" and writer is not None:
                    writer.writeframesraw(command[1])
                    frames += len(command[1]) // 2
                elif kind == "stop":
                    finish(command[1])
                elif kind == "shutdown":
                    finish(command[1])
                    return
        finally:
            if writer is not None:
                writer.close()
