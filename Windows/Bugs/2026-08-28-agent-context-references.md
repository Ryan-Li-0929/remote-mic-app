# Windows agent instructions referenced absent files

## Reproduction

From a public checkout containing the independent Windows baseline, follow
`Windows/AGENTS.md` and try to open the four required `docs/ai_context/*.md` files.

## Observed result

All four paths are absent. The tracked instruction file therefore cannot be followed in a
public clone.

## Expected result

Every mandatory pre-edit document reference resolves to a tracked public file.

## Root cause

The Windows baseline intentionally omitted internal task and handover material from the
public tree, but its tracked agent entry point retained references to those private files.
The existing dead-reference test covered selected `docs/tasks`, `docs/reports`,
`docs/reviews`, and `docs/releases` paths but did not cover `docs/ai_context`.

## Fix

The agent entry point now routes to the tracked Windows README, client README, changelogs,
relevant ADRs, tests, and Git status. Public status belongs in those tracked artifacts.

## Verification

- Read every path in the updated `Read Before Editing` list.
- Run the Windows public-boundary and regression tests.

No macOS product code or release behavior is changed by this documentation repair.
