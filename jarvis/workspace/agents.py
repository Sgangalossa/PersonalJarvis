"""What a workspace terminal can RUN — a small, open registry.

Two kinds of entry live here, and the difference is the whole design:

* **A coding-agent CLI** (Claude Code, Codex, whatever is registered next) — a
  binary that has to be detected, may have to be installed, and is launched by
  name inside a shell.
* **A plain terminal** — this machine's own shell and nothing else. Nothing to
  detect beyond "does this host have a shell", nothing to install, and no agent
  wrapped around it. It is what you want when the job is `git rebase -i`, not
  "ask an agent to do it".

The registry is deliberately open (:func:`register_agent`): a new interactive
CLI is a spec, not a code change spread across detection, launching and the UI.
Everything downstream — the ``/agents`` endpoints, the pane split menu, the
Agentic-IDE grid — reads this list rather than a hardcoded pair of names, so
registering one entry is enough to make it offerable everywhere.

CLI entries reuse ``CliSpec`` so the existing ``CliStatusProber`` can detect
them, but they are deliberately NOT registered in the shared CLI catalog
(``jarvis/clis/catalog/seed_catalog.json``) — see ``__init__`` for why.

Cross-platform: the shell entry resolves through
:func:`jarvis.terminal.shells.default_shell`, which knows pwsh/PowerShell/cmd/
Git Bash on Windows and ``$SHELL``/``/etc/shells`` elsewhere. On a host with no
shell at all (a stripped container) the entry reports itself as not installed
rather than handing the PTY an argv that cannot start.
"""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path
import sys
import time