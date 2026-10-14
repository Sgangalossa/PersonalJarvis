# ADR: Jarvis Command Deck visual language

Date: 2026-10-06
Status: accepted

## Decision

The primary Jarvis surface uses a cinematic HUD language inspired by the interaction hierarchy of Iron Man's JARVIS, without copying Marvel artwork or assets.

The home screen is an operational command deck:
- one dominant conversational/voice core;
- restrained radial/reticle geometry around the active core;
- thin cyan/primary signal lines and state indicators;
- side rails reserved for future real telemetry and intelligence;
- a compact system identity and explicit current interaction mode;
- motion communicates state rather than decorating the screen;
- no invented telemetry, fake percentages, or fake system health.

## Why

Existing Jarvis-style projects commonly stop at decorative neon dashboards, simulated gauges, and a central reactor. That makes a screenshot impressive but makes a real assistant harder to use. Jarvis should instead make the assistant's actual state the visual protagonist.

The visual system therefore separates:
1. **core interaction**: what Jarvis is doing now;
2. **context**: what Jarvis knows or is operating on;
3. **telemetry**: only measured backend state;
4. **controls**: actions the user can actually invoke.

## Roadmap

1. HUD shell and responsive visual grammar.
2. Bind real voice/brain state to the core reticle and status signal.
3. Replace side-rail placeholders with real system, agent, and mission telemetry.
4. Add contextual mode transitions (conversation, research, coding, automation, alert).
5. Add cinematic boot/recovery transitions while respecting reduced-motion preferences.
6. Performance budget: animations remain compositor-friendly and decorative motion stays subordinate to content.
