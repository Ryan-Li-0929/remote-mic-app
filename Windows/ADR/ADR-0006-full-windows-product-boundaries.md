# ADR-0006: Full Windows Product Boundaries

## Status

Accepted for the isolated `codex/windows-full` development track on 2026-08-28.

## Context

The existing Windows RC003 client already provides the product baseline: WinRT BLE/ATVV
voice transport, decoded PCM output, configurable voice shortcuts, ordinary-button
gestures, PySide6/QML settings, diagnostics, and an Inno Setup installer. The user requested
a complete Windows installer without changing the existing macOS application.

Three gaps remain outside the validated baseline:

1. Windows does not reliably expose the RC003 Back, Volume Up, or Volume Down usages to the
   supported user-mode Raw Input path.
2. The live remote-audio meter and temporary Reflections audio retained for at most four
   hours are not implemented in the Windows client.
3. An end-user installer needs an explicit trust and rollback boundary for every driver it
   offers.

## Decision

- Keep all Windows product work inside `Windows/` and Windows-only workflows. Existing
  macOS source, identifiers, packages, update feeds, and workflows are invariants.
- Keep Python/PySide6 as the shipping Windows client for this track. No C++ or WinUI rewrite
  is part of the feature.
- Continue using the vendor-original VB-CABLE Basic package as the optional virtual-audio
  route. Preserve its Donationware identity, origin, license notice, user confirmation, and
  vendor installer. Do not create a custom audio driver.
- Add live level and temporary audio-history functionality above the decoded 16 kHz PCM
  boundary. Disk writes must run on a bounded background queue, never a BLE/audio callback.
- If the three missing physical buttons require a driver, use a device-specific RC003 HID
  filter scoped to VID `0x2717` / PID `0x32B8` and the verified RC003 top-level collections.
  Never install a keyboard class-wide filter.
- The user-mode bridge and the filter communicate through a versioned, read-only device
  interface that carries normalized press/release edges only. It must not carry raw voice
  data, Bluetooth addresses, device paths, or unrelated keyboard events.
- A public or ordinary-user package must contain a Microsoft-trusted driver catalog. An
  unsigned/test-signed filter may be built for CI but must not be included in an end-user
  installer and must not cause the installer to enable Windows test-signing mode.
- Driver installation requires an explicit UAC step. Failure or cancellation leaves the
  user-mode application usable and reports the three affected buttons as unavailable.
- Uninstall and rollback remove only the RC003 device filter, re-enumerate the affected
  device, preserve user configuration/history, and leave unrelated keyboards untouched.

## Verification gates

- Mac isolation: no product diff under `Sources/`, `Resources/`, `Package.swift`, or macOS
  packaging/release workflows.
- User-mode: cross-platform unit tests plus Windows CI for BLE contracts, shortcuts,
  mappings, audio meter, bounded recording, retention, installer upgrade, and uninstall.
- Driver: WDK Release x64 build, static analysis, INF verification, package signature
  verification, device-specific match verification, and rollback tests.
- Hardware: a clean Windows 10 x64 and Windows 11 x64 machine with a real RC003 must verify
  all press/release edges, no duplicate native action, sleep/wake, reconnect, update,
  uninstall, VB-CABLE routing, and Typeless/Qianwen insertion.

Passing CI or building an installer is not physical-device acceptance.
