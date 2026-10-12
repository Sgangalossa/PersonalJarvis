# Product roadmap: reliability, privacy and PARASSITA

Accepted direction: 2026-10-12. The user's proposed capabilities are retained;
delivery order changes to prioritize a usable, verified product. This document
is a backlog, not evidence that the capabilities below are implemented.

## Immediate priority

Finish current reliability and installation qualification before starting
Tor/VPN integration or a full visual redesign. Fix confirmed security defects
immediately in every phase. Coordinate physical-Mac tests through the agent
with authorized local access; remote CI cannot substitute for live receipts.

At the reviewed parent `14ddc0bf`, native package publication is running in
[manual run 38228541954](https://github.com/Sgangalossa/PersonalJarvis/actions/runs/38228541954).
The new CI also exposes a registry quota failure before the no-PortAudio test
and a Windows browser crash-cleanup failure. Inspect exact causes and baseline
evidence before implementation or retry; do not hide failures or enlarge baselines.

## Ordered work

| Phase | Scope | Entry and exit evidence |
| --- | --- | --- |
| 1 | Reliability, existing security defects, installation and physical-Mac qualification | Public native-package links and hashes resolve; relevant CI passes; installation, update, recovery and supported native behavior have real evidence. |
| 2 | Data privacy and lifecycle | Map local and remote data flows; verify removal, export, retention, derived memory, logs and backup recovery across stores. Document residual copies and provider limits. |
| 3 | Existing personal-assistant capabilities | Improve memory continuity, verified execution, bounded autonomy, voice and multimodal use only where measured gaps exist. |
| 4 | PARASSITA private-session foundation | Explicit opt-in, isolated sessions and temporary data, selective persistence, controlled memory context, provider/plugin policy and honest protection states. |
| 5 | PARASSITA protected networking | Integrate mature supported tools, qualify each traffic boundary and prove interruption cannot silently bypass the requested route. |
| 6 | Identity, onboarding and usability refinements | Extend the current profile and setup flow; keep setup progressive and optional and preserve application/update identity. |
| 7 | Complete PARASSITA visual experience | Extend central theme/state tokens across supported views; prove state preservation, accessibility and truthful protection indicators. |

Phases are dependency guides, not rigid silos. A small confirmed prerequisite
may land earlier. Quality, focused tests and documentation accompany every
change; they are never postponed to a final phase. Large network or visual
changes must not delay repairs to the current product.

## Preserved requirements

### Security and privacy

Retain centralized policy and least privilege, OS credential management where
available, input/path/output validation, prompt-injection and exfiltration
defenses, risk-appropriate approvals, timeout/cancellation/recovery and safe
diagnostics. Account for microphone, camera, screen, input, location, browser,
files and connected accounts. Expose real activity and revocation limits.

Distinguish application deletion from forensic erasure, including snapshots,
swap, backups and external provider copies. Verify protected backup and restore
procedures and incident response. Extend existing dependency/security workflows
instead of inventing another scheduler. Updates require provenance/integrity and
an explicit recovery policy; do not market the assistant as an antivirus.

### PARASSITA behavior and network scope

The requested name remains exactly **PARASSITA**, disabled by default.
An active visual mode and a verified network route are separate states.
Protected, partial, unprotected and checking indicators must describe a specific
tested scope, timestamp and limitations, never absolute anonymity.

Evaluate official Tor Browser and existing VPN integrations without custom
cryptography or weakening TLS. Inventory Jarvis, browser, AI-provider, plugin
and external-app traffic separately. Where supported, test route, public IP,
DNS/IPv6/WebRTC exposure, excluded connections, startup, crash, update and route
loss. Suspend covered work on failure instead of silently going direct.
Do not claim a kill switch until containment is enforced and tested.

Keep geolocation permission explicit; distinguish physical location, GPS and
estimated exit-IP region. Support region selection only when the actual service
does. Personal logins, payment details and user-provided identity remain potential
identifiers. Diagnostic network checks themselves contact external services and
must follow the selected privacy policy.

Use isolated browser/session storage, minimize cookies/cache/history and
unnecessary background requests, and preserve deliberate user exports.
Temporary-data cleanup must not erase unrelated system records. Memory,
audio, images, video and transcripts must obey the mode's declared provider
policy. Do not make arbitrary browser customizations that undermine the
adopted tool's fingerprinting defenses.

### PARASSITA visual identity

Retain the full coordinated transformation requested by the user, not merely
a toggle or a generic dark theme: dashboard, chat, settings, projects, memory,
menus, popups, notifications and supported windows. Use an original graphite/
anthracite identity with restrained cyan/teal accents, readable typography and
clear operational indicators. Avoid imitation branding, decorative fake metrics
and aggressive animation.

Extend existing theme tokens and central state. Keep visual preference distinct
from route activation across navigation and restart. Activation/deactivation
must preserve conversations, projects and jobs and explicitly handle private
sessions and suspended connections. Respect light/dark contracts, keyboard
access, contrast, reduced motion and low-resource devices. Perform appropriate
component checks, production build and visual verification.

### Installation, identity and assistant capabilities

Retain guided desktop installation, advanced CLI/headless paths, clean-install/
repair/update/uninstall tests and explicit data-preservation choices. Verify
signatures, notarization and supported-platform claims from real artifacts.

Reuse profile, preferences, onboarding and provider setup. The current assistant
name derives from the wake phrase; separating display name and wake word is an
intentional compatibility change, not a second competing identity setting.
Preserve bundle IDs and update trust. Never require an API key when a supported
deferred or local setup path exists.

Keep the existing orchestrator, safety boundary, memory and extension systems.
Improve planning, evidence-backed results, controlled autonomy and user-editable
memory rather than building duplicates. Keep user/project/agent boundaries and
distinguish facts, assumptions and stale context.

## Execution and coordination

Work only on `jarvis-lab`; PR #1 stays open and draft. No main merge, release,
history rewrite or credential change is implied by this roadmap.
Before each block, inspect current remote state, applicable instructions and the
actual relevant code. Classify requirements as verified, partial, defective,
absent or unverified, with evidence and a concrete next action.

Land small reviewed changes, run proportional checks, publish finished work,
inspect CI and preserve concurrent agent edits. Use repository-approved fakes
for paid services. Do not trigger live paid probes or silently expand permissions.
Repository names, trust roots and application IDs follow the verified maintainer
source of truth rather than speculative replacements.

Completion is scoped per increment. Native tests, external dependencies and
unavailable capabilities stay explicitly unverified until evidence is recorded.
