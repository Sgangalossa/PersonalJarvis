import { lazy, Suspense } from "react";
import { useHomeStore } from "@/store/home";
import { VoiceStage } from "@/components/home/VoiceStage";
import { useT } from "@/i18n";
import "./HomeView.css";

const ChatStage = lazy(() =>
  import("@/components/home/ChatStage").then((module) => ({ default: module.ChatStage })),
);

function HudCorner({ side }: { side: "left" | "right" }) {
  return (
    <aside className={`jarvis-hud-rail jarvis-hud-rail--${side}`} aria-hidden="true">
      <span className="jarvis-hud-rail__label">{side === "left" ? "SYSTEMS" : "INTELLIGENCE"}</span>
      <i /><i /><i />
      <span className="jarvis-hud-rail__signal" />
    </aside>
  );
}

/**
 * The primary Jarvis surface. This is deliberately an operational HUD, not
 * a fake cockpit full of invented telemetry: every future gauge has a defined
 * home for real state, while the visual language already establishes the
 * cinematic hierarchy.
 */
export function HomeView() {
  const t = useT();
  const surface = useHomeStore((s) => s.surface);
  return (
    <div className="jarvis-home" data-testid="home-view" data-surface={surface}>
      <header className="jarvis-home__topline">
        <div className="jarvis-home__identity">
          <span className="jarvis-home__mark">J</span>
          <div>
            <strong>J.A.R.V.I.S.</strong>
            <span>PERSONAL INTELLIGENCE SYSTEM</span>
          </div>
        </div>
        <div className="jarvis-home__mode">
          <span className="jarvis-status-dot" />
          <span>{surface === "voice" ? "VOICE INTERFACE" : "COMMAND INTERFACE"}</span>
          <b>READY</b>
        </div>
      </header>

      <div className="jarvis-home__field">
        <HudCorner side="left" />
        <main className="jarvis-home__core">
          <div className="jarvis-home__reticle" aria-hidden="true">
            <span /><span /><span /><span />
          </div>
          {surface === "chat" ? (
            <Suspense fallback={<div role="status" className="jarvis-home__loading">{t("common.loading")}</div>}>
              <ChatStage />
            </Suspense>
          ) : (
            <VoiceStage />
          )}
        </main>
        <HudCorner side="right" />
      </div>

      <footer className="jarvis-home__footer" aria-hidden="true">
        <span>LOCAL / SECURE CHANNEL</span>
        <span className="jarvis-home__footer-line" />
        <span>NEURAL COMMAND DECK</span>
      </footer>
    </div>
  );
}
