# ADR-0003: Two repos split by content, not by copy

## Status
Accepted — 2026-10-29

## Context
The app's code is meant to be a public portfolio piece (architecture, CI, evals, README), but the real member docs contain personal details about actual friends and must never be public. Some way to separate "shareable engineering" from "private personal data" is required.

## Options considered

**Two repos split by content**
- `bg-center` (public): all code, CI, eval runner, fictional sample members, sample golden set, design doc, ADRs, README, aggregate eval scores.
- `bg-center-data` (private): real member docs, real golden set, real eval outputs — no code.
- Pros: nothing to sync; the public repo's commit history is the real development history; real data literally never enters the public repo's history, so it can't leak through it.
- Cons: local dev needs to point at a sibling checkout of the private repo for real-data work; CI only ever exercises the sample track.

**One private repo with everything, publishing release snapshots to a public repo**
- A GitHub Action, allowlisted and squash-committing, periodically publishes a sanitized snapshot to a public repo.
- Pros: single source of truth; data never has its own repo to manage.
- Cons: the public repo would only ever show point-in-time snapshots, not the real commits/PRs — defeats the "README as portfolio page" goal of showing the actual engineering process.

## Decision
Two repos, split by content:
- `bg-center` — public. All code and engineering artifacts develop here directly; this is the real commit history.
- `bg-center-data` — private. Real member docs, real golden set, real eval outputs. No code.

Data reaches the app via `DATA_DIR`: `data/sample` by default (ships in the public repo), or `../bg-center-data/members` locally when working with real data. In production, the backend either checks out `bg-center-data` at deploy time with a read-only deploy key, or the docs are loaded into Postgres once and read from there.

The public repo `.gitignore`s any local path to the private data, and CI runs secret scanning, so a misplaced file can't be committed by accident.

## Consequences
- Fictional sample data (see `docs/design.md` § Evals) must be actively maintained to mirror the real data's shape (member count, doc length, PT/EN mix, section structure) so that CI on the public repo stays meaningful.
- Every real thumbs-down needs a fictional equivalent manually added to the sample golden set, since the real golden set never appears in CI logs or PR comments.
- Two eval tracks (sample in CI, real run locally/privately before release tags) must be kept in sync in spirit, per `docs/design.md` § "Two eval tracks, one runner".
