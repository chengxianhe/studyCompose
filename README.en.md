# studyCompose

[中文](README.md) | English

A personal reference project on keeping AI-assisted Android development under
architectural control: architecture rules are enforced by machine assertions
(Konsist, detekt, lint, Dependency Guard) instead of living only in documents.

It has two parts, fully isolated from each other:

- a multi-module Jetpack Compose Android app skeleton;
- a standalone "governed AI knowledge platform" prototype (`platform/`). It is not
  part of the Gradle build, and the Android architecture rules do not apply to it.

## What's in this repository

```
app/ feature/* core/* domain/* data/*   Android app, Google's recommended layering + UDF
build-logic/                            Gradle convention plugins
konsistTest/                            Machine assertions for the architecture rules
docs/                                   Architecture, process and AI-collaboration docs
template/                               Reusable scaffold extracted from this project
platform/                               Standalone Python service: knowledge-governance prototype
CLAUDE.md / AGENTS.md                   Hard rules for AI collaborators (AGENTS.md is a symlink to CLAUDE.md)
```

Documents under `docs/` and the rule files are written in Chinese.

## Getting started

### Android part

```bash
bash scripts/verify.sh android  # full gates and debug APK build
```

- See [docs/workflow.md](docs/workflow.md) for the workflow and independent model review; `TASKS.md` tracks active work.
- Read `AGENTS.md` (linked to `CLAUDE.md`) first. Layering, design-system tokens and logging rules are
  hard rules there; violating them turns CI red.
- For how to write a specific kind of feature, look it up in
  `docs/patterns/README.md` and follow the real code it points to.
- To see how the scaffold was built from scratch, read
  `docs/compose-ai-bootstrap-final.md`. To start a new multi-module Compose
  project, use `template/` directly.

### `platform/` (AI knowledge-governance prototype)

```bash
bash scripts/verify.sh platform
```

- It exposes two MCP tools, `knowledge.search` and `knowledge.propose`, configured
  in `.mcp.json` at the repository root. Claude Code and Codex ask whether to
  trust it when you open this repository; once trusted, the tools are available
  in the session.
- For usage, known trust boundaries and implemented checks, see `platform/README.md`.
- For design background and trade-offs, see
  `docs/ai-engineering-governed-delivery-platform.md` (full proposal) and
  `docs/ai-engineering-governed-delivery-platform-baseline.md` (phase-0 decisions
  and acceptance status).

## Current status — don't overestimate it

- Android: Konsist, detekt, lint, tests, Spotless, Dependency Guard and debug APK builds must pass.
  Jacoco/APK size remain advisory. Remote merge blocking also requires branch rules; YAML alone is not proof.
- `platform/`: knowledge approval/search, delivery contracts and Harness state tracking were implemented
  in T-P0–T-P8. This remains a prototype; a real task has not yet completed end-to-end acceptance.
  See `docs/tasks/completed-platform.md`.
- The app now targets local photo management. `TASKS.md` and task handoff notes record progress,
  existing uncommitted work and outstanding performance acceptance.

## Maintenance plan

Two separate escalation paths, one for Android code rules and one for the knowledge base.

**Android: from mistake to rule** (defined in `docs/LESSONS.md`, already in use):

```
one-off mistake   → fix it on the spot, don't record it
repeated twice    → record in docs/LESSONS.md; the AI suggests moving it to the knowledge base
repeated 3 times  → distill into a hard rule in CLAUDE.md
machine-checkable → upgrade to a Konsist / detekt / hook assertion, then delete from LESSONS.md
```

**`platform/` roadmap** (details in §6 of the baseline document):

- Now: phase 0–3 prototype work is archived. Validate real usage when explicitly tasked; do not expand governance automatically.
- Known debt, deliberately deferred: no cleanup job yet for the 90-day audit-log
  retention target (data volume is small); only one project can own a knowledge
  base today, and sharing it across projects needs a "space" isolation concept
  first (§5 of the proposal, intentionally skipped in phase 0).

## Maintainer

A personal project maintained by `chengxianhe`, primarily developed with Codex.
Claude configuration is retained for compatibility. Found a problem or have an idea? Open an issue.

## License

[MIT License](LICENSE) — use, modify and use commercially; just keep the
copyright notice.
