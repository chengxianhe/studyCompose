# studyCompose

[中文](README.md) | English

A local photo library app in development, and a practical project for AI-assisted Android engineering.
The app uses a multi-module Jetpack Compose architecture with automated checks for layering,
design-system rules and dependencies. A separate Python platform manages knowledge review,
task contracts and verification evidence; users retain final review and delivery approval.

## Current capabilities

### Android photo library

| Feature | Status |
|---|---|
| Media permissions and sync | Reads images and videos from MediaStore and syncs lightweight metadata to Room, including incremental changes, deletion reconciliation and time-zone changes |
| Daily timeline | Fixed five-column grid, sticky date headers and a date scrubber; days follow the device time zone, with unknown dates at the bottom |
| On-demand loading | Queries media for visible days, with cancellation, retries and cache eviction; Coil loads thumbnails with bounded caches |
| Four-tab navigation | Navigation 3 maintains separate back stacks; Photos shows the timeline, while Albums, Memories and Editor are placeholders |
| Planned features | Year/month drill-down, album content, on-this-day memories, full-screen viewing, favorites, delete/move and editing are not implemented yet |

Timeline checks pass and some device scenarios have been verified, but **T-014 still needs additional
device validation and human review**. Gaps include RAW thumbnails such as CR3/RAF, the full permission
journey, back navigation and unknown-date scenarios. One million items is a target, not an accepted
performance result; T-012b tracks validation with the real schema, images and scrolling UI.
See [active tasks](TASKS.md) and the [T-014 handoff](docs/tasks/t-014.md).

### Knowledge and task delivery platform

`platform/` is a standalone local Python prototype. It is outside the Gradle build and is not needed
to run the Android app.

- **Knowledge governance:** proposals, catalog and full-text access, human approval/deprecation,
  BM25 and local vector search, plus backup and restore.
- **Local retrieval and provenance:** pinned model revisions/hashes, parent-child chunks, ES hybrid
  retrieval, local reranking, and reviewed source/dependency/replacement relations with impact queries.
- **Host evidence completion:** when internal evidence is incomplete, the host can clarify, research
  public sources or perform authorized checks. Trace validation is not a semantic judge or background agent.
- **Task contracts:** structured acceptance criteria and test cases, version checks, human contract
  freezing and run initiation.
- **Execution evidence:** session commands `prepare / verify / submit / status` connect source snapshots,
  verification runs and acceptance records.
- **Human controls:** a local web interface for knowledge review, task confirmation, manual acceptance
  and final delivery. Agents do not approve on the user's behalf.
- **MCP tools:** `knowledge.list/get/search/propose`, `contract.create/get/update` and
  `harness.record_entry_gate/record_acceptance/get`; see [.mcp.json](.mcp.json).
  Provenance tools include `graph.source_register/propose/get/list/explain/impact`.

The real [T-025](docs/tasks/t-025.md) session workflow received user delivery approval on November 6, 2026.
T-023 and T-014 retain their own outstanding review items. The platform has no background scheduler
that continues development after a session closes. Identity declarations and evidence checks assume
trusted local processes; they do not provide protection against forged identities.
See the [platform README](platform/README.md), [knowledge guide](docs/knowledge/README.md) and
[workflow guide](docs/workflow.md). Detailed project documents are in Chinese.
See [architecture v0.2](docs/knowledge/architecture-v0.2.md) and the
[capability roadmap](docs/knowledge/capability-roadmap.md) for goals, boundaries and gaps.
WeChat and desktop cards are application adapters, not core dependencies.

## Getting started

Run these commands from the repository root.

### Android app

Use JDK 17, as in CI, Android SDK 36 and Python 3. Open the repository in Android Studio,
or configure the SDK path in your local `local.properties`. The minimum supported Android version
is Android 7.0 (API 24).

```bash
# Run all Android gates and build the debug APK
bash scripts/verify.sh android
```

The APK is at `app/build/outputs/apk/debug/app-debug.apk`. You can install and run through Android
Studio; the Photos screen requires the user to grant the relevant media read permissions.

### Local review interface

The platform requires Python 3.11+ and `uv`.

```bash
uv sync --project platform --locked
uv run --project platform python -m govplatform.review
```

Open <http://127.0.0.1:8765/> or the task page at <http://127.0.0.1:8765/tasks>.
The Android app and review interface can be used independently. See the
[platform README](platform/README.md) for MCP integration.

## Verification and delivery

```bash
bash scripts/verify.sh android   # Architecture, static checks, tests, formatting, dependencies and APK
bash scripts/verify.sh platform  # ruff, mypy, pytest and MCP import
bash scripts/verify.sh all       # Both components, including workflow script tests
```

The entry point saves HEAD, before/after source fingerprints, full logs and exit codes under the
local `.verification/` directory. Source changes during a run invalidate the result.
Verification evidence and the platform's runtime database are excluded from Git.

Commit `d4f5f5b` passed `all` on November 9, 2026: 9 workflow tests, the complete Android gates and
120 platform tests. This records automated checks for that version; it does not replace device,
performance or human acceptance. CI uses the same entry point. Remote merge blocking still requires
branch rules; Jacoco and APK-size reporting are advisory.

The November 12 T-031 candidate passed all 192 platform tests without skips, including real local
ES and stdio MCP integration. It adds 24 evidence-trace tests; four of six host cases contain real
tool observations and two are explicitly marked replay. Task records retain human review and
unverified scopes; these checks do not imply final delivery approval.

## Repository structure

```text
app/                  App entry, four-tab navigation and dependency assembly
feature/library/      Daily timeline; module intended to share future album/memory UI
feature/home/         Retained permissions and sync-status screen
domain/               Pure Kotlin entities, repository interfaces and use cases
data/                 MediaStore, Room, sync and repository implementations
core/                 Design system, shared UI, logging and common utilities
build-logic/          Gradle convention plugins
konsistTest/          Architecture and design-rule assertions
benchmark*/           Performance tests and benchmark target app
platform/             Independent knowledge and task delivery platform
scripts/              Verification entry point and source fingerprinting
docs/                 Task handoffs, architecture, evidence and workflow guides
template/             Reusable scaffold reference
```

Dependencies follow `app → feature → domain ← data`; features may depend on core, but not on other
features or data directly. UI follows unidirectional data flow. ViewModels access business logic
through use cases and expose StateFlow. Visual tokens belong to the design system and user-facing
text belongs in string resources.

Before development, read [AGENTS.md](AGENTS.md), which links to [CLAUDE.md](CLAUDE.md), and the
[real-code pattern index](docs/patterns/README.md). Implementers run automated checks; users perform
final code review. Independent model review is not enabled by default. See the
[architecture bootstrap guide](docs/compose-ai-bootstrap-final.md) for background; current project
rules take precedence over historical workflow descriptions.

## Maintenance and license

A personal project maintained by `chengxianhe`, primarily developed with Codex, with Claude
configuration retained for compatibility. Issues and suggestions are welcome. [MIT License](LICENSE).
