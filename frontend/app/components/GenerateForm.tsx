"use client";

import { useState } from "react";

const STOIC_TOPICS = [
  "Overcoming Fear",
  "The Obstacle is the Way",
  "Memento Mori",
  "Amor Fati",
  "Discipline is Freedom",
  "The Inner Citadel",
  "Stoic Resilience",
  "Ego is the Enemy",
  "Morning Meditation",
  "Controlling Your Mind",
  "The Art of Not Reacting",
  "Stillness is the Key",
  "Virtue Above All",
  "Voluntary Hardship",
  "Why Comfort is Your Enemy",
];

// 10 voices grouped by region
const VOICE_GROUPS = [
  {
    region: "🇬🇧 British — Most Popular for Philosophy",
    voices: [
      { id: "gb_ryan",   label: "Ryan",   desc: "Deep • Commanding • Best for Stoicism" },
      { id: "gb_thomas", label: "Thomas", desc: "Warm • Mature • Marcus Aurelius tone"  },
      { id: "gb_sonia",  label: "Sonia",  desc: "Powerful • Elegant • Female"           },
    ],
  },
  {
    region: "🇺🇸 American",
    voices: [
      { id: "us_christopher", label: "Christopher", desc: "Deep • Authoritative • Documentary" },
      { id: "us_andrew",      label: "Andrew",      desc: "Calm • Confident • Ryan Holiday"    },
      { id: "us_eric",        label: "Eric",        desc: "Strong • Motivational • Clear"      },
    ],
  },
  {
    region: "🇮🇳 Indian English",
    voices: [
      { id: "in_prabhat", label: "Prabhat", desc: "Deep • Resonant • Philosophical"   },
      { id: "in_neerja",  label: "Neerja",  desc: "Expressive • Warm • Unique accent" },
    ],
  },
  {
    region: "🇦🇺 Australian  •  🇮🇪 Irish",
    voices: [
      { id: "au_william", label: "William", desc: "🇦🇺 Deep • Grounded • Documentary feel" },
      { id: "ie_connor",  label: "Connor",  desc: "🇮🇪 Poetic • Profound • Celtic depth"  },
    ],
  },
];

// Video length options — two groups
type LengthId = "short" | "medium" | "long_3" | "long_5" | "long_7" | "long_11";

interface LengthOption {
  id: LengthId;
  label: string;
  duration: string;
  beats: number;
  type: "short" | "long";
  icon: string;
}

const LENGTH_OPTIONS: LengthOption[] = [
  // Shorts / Reels
  { id: "short",   label: "Short",    duration: "~35s",    beats: 7,   type: "short", icon: "⚡" },
  { id: "medium",  label: "Medium",   duration: "~60s",    beats: 12,  type: "short", icon: "▶️" },
  // Full YouTube
  { id: "long_3",  label: "3 min",    duration: ">3 min",  beats: 34,  type: "long",  icon: "🎬" },
  { id: "long_5",  label: "5 min",    duration: ">5 min",  beats: 56,  type: "long",  icon: "🎬" },
  { id: "long_7",  label: "7 min",    duration: ">7 min",  beats: 78,  type: "long",  icon: "🎬" },
  { id: "long_11", label: "11 min",   duration: ">11 min", beats: 122, type: "long",  icon: "🎬" },
];

export interface GenerateOptions {
  topic: string;
  length: LengthId;
  aspect_ratio: string;
  voice: string;
  fps: number;
}

interface GenerateFormProps {
  onSubmit: (opts: GenerateOptions) => void;
  isGenerating: boolean;
  channel: {
    id: string;
    name: string;
    topics: string[];
    default_voice: string;
    default_aspect: string;
    default_length: string;
  };
  accentColor: string;
}

const labelStyle: React.CSSProperties = {
  display: "block",
  fontSize: "0.72rem",
  letterSpacing: "0.14em",
  color: "var(--text-muted)",
  textTransform: "uppercase",
  marginBottom: 10,
};

export default function GenerateForm({ onSubmit, isGenerating, channel, accentColor }: GenerateFormProps) {
  const accent = accentColor || "#C4A064";

  const [topic,       setTopic]       = useState("");
  const [length,      setLength]      = useState<LengthId>((channel.default_length as LengthId) || "short");
  const [aspectRatio, setAspectRatio] = useState(channel.default_aspect || "9:16");
  const [voice,       setVoice]       = useState(channel.default_voice || "gb_ryan");
  const [voiceOpen,   setVoiceOpen]   = useState(false);

  // Reset defaults when channel changes
  // (handled by parent via key prop if needed)

  const selectedVoice = VOICE_GROUPS
    .flatMap(g => g.voices)
    .find(v => v.id === voice) ?? { label: "Ryan", desc: "Deep • British Male" };

  const selectedLength = LENGTH_OPTIONS.find(l => l.id === length) ?? LENGTH_OPTIONS[0];
  const isLongForm = selectedLength.type === "long";

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!topic.trim()) return;
    onSubmit({ topic: topic.trim(), length, aspect_ratio: aspectRatio, voice, fps: 30 });
  };

  // Channel-specific topic chips (first 10)
  const topicChips = (channel.topics || []).slice(0, 10);

  return (
    <form onSubmit={handleSubmit} style={{ display: "flex", flexDirection: "column", gap: 24 }}>

      {/* ── Topic Input ── */}
      <div>
        <label style={{
          display: "block",
          fontFamily: "'Cinzel', serif",
          fontSize: "0.75rem",
          letterSpacing: "0.15em",
          textTransform: "uppercase",
          color: accent,
          marginBottom: 10,
          transition: "color 0.4s ease",
        }}>
          {channel.id === "tech" ? "Tech / AI Topic" : "Stoic Topic or Concept"}
        </label>
        <input
          id="topic-input"
          className="input-field"
          type="text"
          value={topic}
          onChange={e => setTopic(e.target.value)}
          placeholder={
            channel.id === "tech"
              ? "e.g. How AI Agents Are Changing Everything..."
              : "e.g. Overcoming Fear through Stoicism..."
          }
          maxLength={150}
          disabled={isGenerating}
          required
        />
        <p style={{ fontSize: "0.78rem", color: "var(--text-muted)", marginTop: 8 }}>
          History tracking ensures zero repeated content across all videos
        </p>
      </div>

      {/* ── Quick Topics (channel-specific) ── */}
      <div>
        <p style={{ fontSize: "0.72rem", color: "var(--text-muted)", marginBottom: 10, letterSpacing: "0.1em" }}>
          QUICK SELECT · {channel.name}
        </p>
        <div style={{ display: "flex", flexWrap: "wrap", gap: 7 }}>
          {topicChips.map(t => (
            <button
              key={t} type="button"
              onClick={() => setTopic(t)}
              disabled={isGenerating}
              style={{
                padding: "5px 12px",
                borderRadius: 50,
                border: `1px solid ${accent}35`,
                background: `${accent}10`,
                color: `${accent}cc`,
                fontSize: "0.72rem",
                cursor: isGenerating ? "not-allowed" : "pointer",
                transition: "all 0.2s ease",
                opacity: isGenerating ? 0.5 : 1,
              }}
              onMouseEnter={e => {
                if (!isGenerating) {
                  (e.target as HTMLElement).style.background = `${accent}22`;
                  (e.target as HTMLElement).style.borderColor = `${accent}60`;
                }
              }}
              onMouseLeave={e => {
                (e.target as HTMLElement).style.background = `${accent}10`;
                (e.target as HTMLElement).style.borderColor = `${accent}35`;
              }}
            >
              {t}
            </button>
          ))}
        </div>
      </div>

      {/* ── Video Length ── */}
      <div>
        <label style={labelStyle}>Video Length</label>

        {/* Group: Shorts / Reels */}
        <div style={{ marginBottom: 10 }}>
          <div style={{
            fontSize: "0.68rem", letterSpacing: "0.1em",
            color: "var(--text-muted)", marginBottom: 6,
          }}>
            ⚡ SHORTS / REELS
          </div>
          <div style={{ display: "flex", gap: 8 }}>
            {LENGTH_OPTIONS.filter(l => l.type === "short").map(opt => (
              <button
                key={opt.id} type="button" id={`length-${opt.id}`}
                className={`option-btn ${length === opt.id ? "selected" : ""}`}
                onClick={() => { setLength(opt.id); if (opt.type === "short") setAspectRatio("9:16"); }}
                disabled={isGenerating}
                style={{ flex: 1 }}
              >
                <span style={{ display: "block", fontWeight: 700 }}>{opt.label}</span>
                <span style={{ display: "block", fontSize: "0.72rem", opacity: 0.7 }}>{opt.duration}</span>
              </button>
            ))}
          </div>
        </div>

        {/* Group: Full YouTube */}
        <div>
          <div style={{
            fontSize: "0.68rem", letterSpacing: "0.1em",
            color: "var(--gold-dim)", marginBottom: 6,
          }}>
            🎬 FULL YOUTUBE VIDEO
          </div>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 8 }}>
            {LENGTH_OPTIONS.filter(l => l.type === "long").map(opt => (
              <button
                key={opt.id} type="button" id={`length-${opt.id}`}
                className={`option-btn ${length === opt.id ? "selected" : ""}`}
                onClick={() => setLength(opt.id)}
                disabled={isGenerating}
                style={{ padding: "10px 4px" }}
              >
                <span style={{ display: "block", fontWeight: 700, fontSize: "0.9rem" }}>{opt.label}</span>
                <span style={{ display: "block", fontSize: "0.68rem", opacity: 0.7 }}>{opt.beats} beats</span>
              </button>
            ))}
          </div>
        </div>

        {/* Long-form info banner */}
        {isLongForm && (
          <div style={{
            marginTop: 10,
            padding: "10px 14px",
            background: "rgba(196, 160, 100, 0.08)",
            border: "1px solid rgba(196, 160, 100, 0.25)",
            borderRadius: "var(--radius-md)",
            fontSize: "0.78rem",
            color: "var(--text-muted)",
          }}>
            🎬 <strong style={{ color: "var(--gold-primary)" }}>Full YouTube format</strong>
            {" "}— Chapter structure: Hook → Problem → Philosophy → Story → Application → Close.
            Generation takes <strong style={{ color: "var(--text-secondary)" }}>~3-5 min</strong> for long videos.
          </div>
        )}
      </div>

      {/* ── Aspect Ratio (hidden for long-form YouTube) ── */}
      {!isLongForm && (
        <div>
          <label style={labelStyle}>Aspect Ratio</label>
          <div style={{ display: "flex", gap: 8 }}>
            {["9:16", "16:9", "1:1"].map(r => (
              <button key={r} type="button" id={`ratio-${r.replace(":", "-")}`}
                className={`option-btn ${aspectRatio === r ? "selected" : ""}`}
                onClick={() => setAspectRatio(r)} disabled={isGenerating}
                style={{ flex: 1, fontSize: "0.8rem" }}>
                {r}
              </button>
            ))}
          </div>
        </div>
      )}
      {isLongForm && (
        <div style={{
          padding: "10px 14px",
          background: "var(--bg-elevated)",
          borderRadius: "var(--radius-md)",
          fontSize: "0.78rem",
          color: "var(--text-muted)",
        }}>
          📐 <strong>Aspect Ratio:</strong> 16:9 (YouTube horizontal) — auto-set for full-length videos
        </div>
      )}

      {/* ── Voice Selector ── */}
      <div>
        <label style={labelStyle}>Narrator Voice · Deep Neural TTS + Bass Chain</label>

        <button
          type="button" id="voice-selector-toggle"
          onClick={() => setVoiceOpen(o => !o)}
          disabled={isGenerating}
          style={{
            width: "100%", padding: "12px 16px",
            background: "var(--bg-elevated)",
            border: "1px solid var(--border-gold)",
            borderRadius: "var(--radius-md)",
            color: "var(--text-primary)",
            cursor: "pointer",
            display: "flex", alignItems: "center", justifyContent: "space-between",
            fontSize: "0.9rem", fontWeight: 600,
          }}
        >
          <span>
            {selectedVoice.label}
            <span style={{ fontWeight: 400, color: "var(--text-muted)", fontSize: "0.8rem" }}>
              {" "}— {selectedVoice.desc}
            </span>
          </span>
          <span style={{ fontSize: "0.7rem", color: "var(--gold-primary)", letterSpacing: "0.1em" }}>
            {voiceOpen ? "▲ CLOSE" : "▼ CHANGE"}
          </span>
        </button>

        {voiceOpen && (
          <div style={{
            marginTop: 8,
            background: "var(--bg-elevated)",
            border: "1px solid var(--border-subtle)",
            borderRadius: "var(--radius-md)",
            overflow: "hidden",
          }}>
            {VOICE_GROUPS.map(group => (
              <div key={group.region} style={{ borderBottom: "1px solid var(--border-subtle)" }}>
                <div style={{
                  padding: "8px 14px",
                  fontSize: "0.68rem", letterSpacing: "0.12em",
                  color: "var(--gold-dim)", textTransform: "uppercase",
                  background: "var(--bg-glass)",
                }}>
                  {group.region}
                </div>
                <div style={{
                  display: "grid",
                  gridTemplateColumns: "repeat(auto-fill, minmax(140px, 1fr))",
                  gap: 1, background: "var(--border-subtle)",
                }}>
                  {group.voices.map(v => (
                    <button
                      key={v.id} type="button" id={`voice-${v.id}`}
                      onClick={() => { setVoice(v.id); setVoiceOpen(false); }}
                      style={{
                        padding: "10px 12px",
                        background: voice === v.id ? "var(--gold-glow)" : "var(--bg-elevated)",
                        border: "none",
                        borderLeft: voice === v.id ? "2px solid var(--gold-primary)" : "2px solid transparent",
                        cursor: "pointer", textAlign: "left",
                      }}
                    >
                      <span style={{
                        display: "block", fontSize: "0.84rem",
                        fontWeight: voice === v.id ? 700 : 500,
                        color: voice === v.id ? "var(--gold-primary)" : "var(--text-primary)",
                      }}>
                        {v.label}
                      </span>
                      <span style={{ display: "block", fontSize: "0.72rem", color: "var(--text-muted)" }}>
                        {v.desc}
                      </span>
                    </button>
                  ))}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* ── Submit ── */}
      <button
        type="submit" id="generate-btn"
        disabled={isGenerating || !topic.trim()}
        style={{
          width: "100%", fontSize: "1rem", padding: "18px",
          border: "none", borderRadius: "var(--radius-md)",
          background: isGenerating || !topic.trim()
            ? "rgba(255,255,255,0.06)"
            : `linear-gradient(135deg, ${accent}, ${accent}bb)`,
          color: isGenerating || !topic.trim() ? "var(--text-muted)" : "#0d0d12",
          fontWeight: 800, letterSpacing: "0.06em",
          cursor: isGenerating || !topic.trim() ? "not-allowed" : "pointer",
          transition: "all 0.3s ease",
          boxShadow: isGenerating || !topic.trim() ? "none" : `0 4px 24px ${accent}40`,
          fontFamily: "'Cinzel', serif",
          display: "flex", alignItems: "center",
          justifyContent: "center", gap: 10,
        }}
      >
        {isGenerating ? (
          <>
            <span style={{
              width: 18, height: 18,
              border: "2px solid rgba(0,0,0,0.3)",
              borderTopColor: "#0d0d12",
              borderRadius: "50%", display: "inline-block",
              animation: "spin-slow 0.8s linear infinite",
            }} />
            {isLongForm ? "Generating full video (this takes a few minutes)..." : "Generating..."}
          </>
        ) : (
          <>
            <span>{isLongForm ? "🎬" : "⚡"}</span>
            {isLongForm
              ? `Generate Full ${selectedLength.duration} YouTube Video`
              : `Generate ${channel.id === "tech" ? "Tech" : "Cinematic"} Short`}
          </>
        )}
      </button>

      <style>{`@keyframes spin-slow { to { transform: rotate(360deg); } }`}</style>
    </form>
  );
}
