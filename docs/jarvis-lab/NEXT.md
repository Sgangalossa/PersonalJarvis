# JARVIS-LAB next remote frontier

Verified on 2026-10-05 after the latest autonomous blocks: reminder scheduling is now exposed as a real Brain tool, preserves the originating turn trace into TaskScheduler, is classified as a write tool (hidden on signalless and screenshot turns), and has a registered capability with EN/DE/IT intent coverage. The installer-smoke release lookup is authenticated, the recent Cost-attribution series is restored and the GPT-Live voice-preview path is now hardened against incomplete session closure. **Exact branch HEAD is deliberately not copied into this file: this document changes HEAD when it is committed. Use the GitHub `jarvis-lab` branch endpoint as the authoritative SHA.** The newest blocks must not be described as green until their active CI run completes.

## 2026-10-05 continuous reliability state
- `9896a04`: Windows CI exposed that the persisted-room-recovery regression was seeding no claim; the fixture now creates the claim through the real `SocietyScheduler.drive_room()` path before simulating restart.
- `308a82f`: task-step sequence allocation is now atomic at the SQLite INSERT boundary, with a concurrent-writer regression preventing `(task_id, seq)` collisions.
- `c1093c8`: the audio player now has a focused regression proving `AudioOutFirst` is published exactly once and only after the first real PortAudio write.
- `8e7ced0`: live Society room settlement now has a focused provenance regression preserving the exact room-open event ID, trace ID, room ID and requesting chat session in the projected result notice.
- `f7278be`: durable Society room recovery now has a focused regression proving a persisted in-flight claim is resumed with the exact original `claim_id` after scheduler restart; no second claim is synthesized.

Last recorded reliability checkpoint below is historical context, not the authoritative current HEAD. Re-read the branch endpoint before acting.

Recent reliability checkpoints now on the branch:
- `10ae037`: unpinned fallback provider models no longer get clobbered by static tier defaults.
- `c372ca5`: Society room test fixture accepts the restricted `read_only` turn contract.
- `27b3018`: custom CLI aliases and call-sign reservations preserve hyphenated slugs.
- `e601c95`: the frontier integration gap is closed in the code path: opt-in lazy refresh runs from `BrainManager.generate()` before the first real turn, and the bug register records CI qualification as pending.
- `bd5358f`: a RESULT carrying another agent's live `run_id` can no longer release that agent's scheduler slot.
- `157afa2`: malformed terminal RESULTs now release the sender's owned run slot instead of stranding concurrency.
- `549337a`: duplicate T3 remote-agent documentation was removed from `docs/os-parity.md`.

Current CI qualification is still asynchronous on the latest published commits. Do not mark these newest checkpoints green until the corresponding workflow completes; failures must be triaged by new regression IDs rather than by expanding baselines.

Native macOS qualification remains separate and requires a physical Mac with Accessibility/input permission. It must not be represented as remotely complete.


Verified on 2026-10-05: the lead-chat event-routine creation and connection-path readback contract is present at `094a2d4`. Its CI #213 passed static gates, contracts, frontend and the completed portable shards while newer branch activity superseded two Windows shards. PR #1 remains open and draft.

M4 room scheduling is no longer the next unblocked task. The branch now carries bounded live-room scheduling through the existing `SocietyScheduler`, restart recovery, voice completion/status, curator review/taint invariants, and blocking exit contracts. M5 hardening guards are also present for legacy Agents routing, Jarvis-only production seeding, capability-driven teammate proposals, the canonical Society cost surface, locale/enum parity, boot budget, and Ledger accessibility.

M6 already includes learned-skill review, signed GitHub merged-PR triggers, isolated screen leases and validated shareable figure recipes. Lead-chat event routine schemas and agent-chat save mandates are present. Italian schedule/event intent now uses the same routing and save guards, with focused tests excluding habits, how-to questions and skill authoring. These are implemented slices, not complete native qualification.

Current qualification: `9d29df9` adds the full signed-delivery contract, from lead-chat routine creation through the existing credential route, merge filtering, replay deduplication, owned execution and result readback without credential disclosure. CI #220 (`37284242791`) passed static gates; portable test shards were still running at this check. The branch also carries durable routine readback (`b4a4885`), client-zone updates (`a68ff94`), REST opener provenance (`3650b5c`) and cancellation/cost recovery through the existing scheduler (`99d4ee4`). These changes remain subject to the latest complete CI result.

Bounded room-watcher recovery now cancels the exact owned turn after three event-read failures, reads available terminal cost, fails the durable claim and releases the scheduler slot. Dispatch cancellation and lost-claim subscription cleanup also have deterministic regressions. Runner qualification remains pending for these additions.

Signed routine receipt contracts now cover active and paused ownership, owner-seat failure, temporary admission deferral, queued database reopen and claimed-delivery interruption. They use the real TaskStore, TaskRunner and TaskScheduler through authenticated GitHub ingress and verify no generic model fallback, retained pending delivery and no replay of potentially executed work (4414438, 9332744). CI #222 exposed one new test error: a timezone-bearing one-shot update was incorrectly expected to pass the recurring-only routine contract. f81a719 preserves the 409 rejection and checks that the durable spec and timezone context remain unchanged. Baselines were not expanded.

The owner runner now fails closed when the saved task or its model seat cannot be read, instead of silently substituting the owner's live seat. Focused contracts require zero new run chats and no main-chat mutation on missing or unreadable storage. Runner qualification is pending for this change and the signed-receipt additions.

CI #226 (37288552623) is now complete: every portable, Windows, frontend, contracts, static, installer, updater and browser job passed; the three native Mac lanes remain the documented skips. The owner seat and signed-delivery changes are therefore qualified by the full portable run. The SocietyScheduler now logs a deferred busy-recipient receipt while retaining the durable queue retry (35a416c).

CI #230 (37291147213) is complete and green across all portable, Windows, frontend, contracts, static, installer, updater and browser lanes; the three native Mac lanes remain documented skips. Busy Society deliveries now log both the primary and same-recipient retry deferral paths while retaining the durable queued state, covered by test_busy_delivery_stays_queued_and_is_logged. This closes the remote observability slice.

CI #232 on `5657fcd` is complete and green. Owner-facing routine readback now includes the latest execution outcome, error and a result bounded to 400 characters from the existing TaskStore. An older success is withheld during a running or failed execution. Contracts exercise signed delivery outcomes, database reopen, result bounds and owner isolation. Qualification of this new slice is pending its own CI.

The Automations list and detail API now apply the same outcome guard: a running, failed, cancelled or interrupted run cannot display an earlier success as its current result. Historical result steps remain available for inspection. Focused API contracts cover each outcome; full portable qualification is pending.

The next remote-safe step is an audit of durable handoff receipts around scheduler recovery and room result projection. Preserve exact event IDs, retry state and owner accounting through the existing scheduler; add only a focused regression when a real gap is found. Native Mac qualification remains blocked on physical Accessibility and input permissions.

Recovery update (2026-10-05): the 14 uploaded Abacus patches cover the local series `6db4291..2770019`, based on `5657fcd` (CI #232 green). They recover durable RESULT handoffs, Society runtime cleanup, process-wide runtime/factory isolation, cost-route indexer isolation, server-side privacy-log assertions, and the shipped ink-tile icon contract. The icon's obsolete Linux/Windows baseline entries are removed; no failure baseline is expanded.

Integration review excluded the unrelated provider-default change from patch 13, which made primary and fallback identical. It also closed a crash window in patch 1: RESULT handoffs now enter the delivery queue in the same SQLite insertion as their event. Queue recovery validates the RESULT before forwarding it, retaining the original event ID and durable recipient. New interrupted-publication tests failed against the uploaded implementation before this correction and pass afterward. Test runtimes close in cleanup paths, including failed test bodies.

The originating agent reported 4,225 passing tests and an exact-base comparison of VM-specific failures. Those are transferred reports, not independently verified results here; its final full shard rerun had not completed. Independent validation in this workspace: 2,404 passed, 26 skipped, zero failures across Society, agent-chat, commands, contracts and the affected icon, route and desktop-start suites on Linux/Python 3.12. The first pass exposed a missing `socksio` dependency in this proxy-enabled environment; the rerun passed after installing it, without code or baseline changes. Changed Python files pass Ruff. The concurrent routine-readback commits `c3b3574` and `57d9355` are retained. GitHub CI will qualify the published integration commit; native Mac evidence remains separate.

Native MacAgentBench qualification remains explicitly deferred to a physical Mac with user-granted permissions and must not be represented as remotely complete.

## 2026-10-05 continuous reliability checkpoints

The current `jarvis-lab` line includes these verified code-level checkpoints:
- `1a13210` forces Society room turns through the chat `read_only` contract.
- `0720563` adds a focused room-dispatch regression test.
- `145a617` authenticates the installer smoke GitHub `/releases/latest` lookup while preserving the 404/no-release skip.
- `fc62663` updates custom-CLI tests to avoid the now built-in `antigravity` id collision.
- `f374ac1` + `c39d0cb` recheck live Society grants, session provenance and permission policy at tool execution time; a selected tool is no longer trusted indefinitely after the turn starts.
- `d86ac89` restores BrowserTool writability after a temporary `plan`/`read-only` session instead of leaving a reused browser tool permanently restricted.
- `04186f2`, `95c80c2` and `a0b0b8b` cover live grant revocation, live session-mode changes, browser state restoration and canonical Society session provenance.
- `77644d6` fixes the Ollama dictation test to patch the actual provider-endpoint resolver rather than replacing the entire config loader.
- `01965ef` cleans the live-policy test fixtures and keeps the regression suite compatible with the restricted-room contract.

The historical Frontier integration note is resolved in current code: `BrainManager.generate()` invokes the opt-in lazy frontier refresh before the first real turn, guarded by an async lock and skipped for explicit per-turn overrides. `docs/BUGS.md` records the implementation and focused regression coverage. Final CI qualification remains governed by the active workflow run; native macOS qualification remains separate.

Native macOS qualification remains separate and requires physical Accessibility/input permission; remote CI must not be described as MacAgentBench evidence.

- `0837962` persists MissionCompleted subject deduplication in task steps and adds a restart regression, so a scheduler restart cannot replay the same mission-triggered automation.

- `3cdeb93` atomically claims scheduled task runs in `TaskStore` and guards `TaskRunner` against concurrent duplicate execution, with a focused single-flight regression.

- `205c550` makes task state transitions compare-and-swap across runner completion, deferral and scheduler cancellation, with cancellation losing no scheduler-memory state.

- `3cf2fba` preserves `run_now` on paused recurring tasks after the single-flight runner claim was introduced, restoring the paused state only after a successful CAS.

- `642b54c` makes pause use the same state CAS as cancellation, so a task that starts running between the read and the pause request is not silently paused or removed from the scheduler index.

- `db14ae4` makes resume use a paused-state CAS, preventing a concurrent cancellation from resurrecting a paused task as scheduled.

- `48317d2` adds a scheduler regression proving `pause()` cannot win a race against an already-running task.

- `d4ee0ff` makes paused `run_now` restoration CAS-safe and only re-registers the task when its persisted spec still exists.

- `789f104` atomically claims pending durable hook deliveries, closing the scheduler restart/dual-drainer window before external task execution.
- `4ab1a97` fixes durable hook execution to claim the pending delivery before marking or executing it; `ee9de0b` adds the concurrent-drainer regression proving one delivery reaches the runner once.

- `1e03e81` makes max-firing completion cleanup CAS-safe, so late cleanup cannot overwrite a task that has already failed or been cancelled.
- `76f8726` makes durable hook delivery claiming single-flight per task across concurrent drainers, so two different pending deliveries cannot both enter the runner; `6894e6a` extends the regression to prove the second delivery remains pending.
- `b8be072` removes ordering assumptions from the concurrent hook single-flight regression; either delivery may win the claim, but exactly one must finish while the other stays pending.

- CI #438 exposed two scheduler regressions in the active branch. Paused `run_now` now removes the recurring task from every in-memory dispatch structure after restoring its durable paused state, and the concurrent pause guard imports the trigger and conflict types it exercises. The two focused regressions pass locally with Ruff clean; full CI qualification remains pending.

- CI #438 also exposed duplicate `AudioOutFirst` receipts across sentence-level `play_chunks()` calls sharing one persistent output stream. The receipt flag now follows the native stream lifetime and resets only when a replacement stream opens; the focused persistent-stream regression passes with Ruff clean.
