# RemoteMic Windows Agent Entry Point

## Mission

Deliver a usable RC003 Windows remote microphone from the existing validated behavior.

The original short delivery track remains frozen as the user-mode baseline. A separate,
user-approved full-product track may add Windows-only capabilities when it has its own
branch, ADR, tests, rollback path, and release gate. The full-product track must not change
the macOS source tree, bundle identity, update feed, package, or release workflow.

Keep the current Python/PySide6 application as the product baseline. Do not start a C++ or
WinUI rewrite. Do not create a custom audio driver while the distributable VB-CABLE Basic
route remains viable. A device-specific RC003 HID filter may be developed only under the
full-product ADR; it must never be installed as a class-wide keyboard filter and must never
ship unsigned or require Windows test-signing mode in an end-user package.

## Read Before Editing

1. `README.md`
2. `apps/windows/rc003/README.md`
3. `CHANGELOG.md` and `apps/windows/rc003/CHANGELOG.md`
4. Relevant tracked ADR, module documentation, and tests
5. `git status --short`

## Mandatory Rules

- Inspect first, then modify.
- Preserve unrelated and uncommitted user changes.
- Keep secrets, tokens, Bluetooth addresses, UUIDs, voice data, and personal paths out of source control and production logs.
- A build is not proof of BLE, HID, audio endpoint, installer, or target-application behavior.
- Without a physical RC003, mark hardware validation `deferred`; never report it as passed.
- Keep production audio buffers bounded. Do not perform blocking file or process operations in an audio callback.
- New architecture or scope changes require an ADR.
- Keep public status in the relevant changelog, test manual, and ADR. Do not reference
  gitignored or untracked internal handover files from tracked instructions.
- Installer releases must support in-place upgrade: keep the stable AppId and
  install location, stop the old app, replace only versioned program payload,
  preserve config/key mappings/statistics/logs, and leave one installed-app
  entry. Never require the user to uninstall or delete an older installed
  version first. Portable ZIPs are exempt and must not be presented as
  auto-updating.

## Two-Agent Handover

GPT prepares the baseline, resolves high-priority blockers, runs the smallest relevant regression, and writes an executable handover. OpenCode/MiniMax M3 must first read the required files, inspect Git state, restate the current task, and run the handover's first safe command. It must not redesign the project during its first turn.

## Verification Vocabulary

- `passed`: actually executed and observed.
- `failed`: executed and did not meet the stated expectation.
- `deferred`: requires unavailable hardware, external app, account, or environment.
- `not_applicable`: the change cannot affect that boundary.
