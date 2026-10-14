import { Activity, MessageSquare, Radio } from "lucide-react";

import { useEventStore } from "@/store/events";
import { useHomeStore } from "@/store/home";

export function HomeHeader() {
  const assistantName = useEventStore((s) => s.assistantName);
  const voiceState = useEventStore((s) => s.voiceState);
  const surface = useHomeStore((s) => s.surface);

  return (
    <header className="jarvis-home-header" data-testid="home-header">
      <div className="jarvis-home-brand">
        <span className="jarvis-home-brand-mark" aria-hidden><span /><span /><span /></span>
        <div><span className="jarvis-command-kicker">PERSONAL COMMAND SYSTEM</span><strong>{assistantName}</strong></div>
      </div>
      <div className="jarvis-home-header-center" aria-hidden><span /><span>SECURE SESSION</span><span /></div>
      <div className="jarvis-home-link-state">
        {surface === "voice" ? <Radio className="h-3.5 w-3.5" /> : <MessageSquare className="h-3.5 w-3.5" />}
        <span>{surface === "voice" ? "VOICE / " + voiceState.toUpperCase() : "CHAT / READY"}</span>
        <Activity className="h-3 w-3 text-primary" />
      </div>
    </header>
  );
}
