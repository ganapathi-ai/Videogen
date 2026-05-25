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
  "Living in the Present",
  "Virtue Above All",
  "Voluntary Hardship",
  "Finding Stillness",
];

// 15 voices grouped by region — matches backend VOICE_PRESETS
const VOICE_GROUPS = [
  {
    region: "🇺🇸 American",
    voices: [
      { id: "us_male_deep",   label: "Christopher", desc: "Deep • Male"   },
      { id: "us_male_calm",   label: "Andrew",      desc: "Calm • Male"   },
      { id: "us_female_warm", label: "Aria",        desc: "Warm • Female" },
      { id: "us_female_clear",label: "Jenny",       desc: "Clear • Female"},
    ],
  },
  {
    region: "🇬🇧 British",
    voices: [
      { id: "gb_male_rich",     label: "Ryan",   desc: "Rich • Male"     },
      { id: "gb_male_warm",     label: "Thomas", desc: "Warm • Male"     },
      { id: "gb_female_elegant",label: "Sonia",  desc: "Elegant • Female"},
    ],
  },
  {
    region: "🇮🇳 Indian",
    voices: [
      { id: "in_female_expressive", label: "Neerja Pro", desc: "Expressive • Female" },
      { id: "in_female_clear",      label: "Neerja",     desc: "Clear • Female"      },
      { id: "in_male_deep",         label: "Prabhat",    desc: "Deep • Male"         },
    ],
  },
  {
    region: "🇦🇺 Australian",
    voices: [
      { id: "au_female", label: "Natasha", desc: "Female" },
      { id: "au_male",   label: "William", desc: "Male"   },
    ],
  },
  {
    region: "🇨🇦 Canadian",
    voices: [
      { id: "ca_female", label: "Clara", desc: "Female" },
      { id: "ca_male",   label: "Liam",  desc: "Male"   },
    ],
  },
  {
    region: "🇮🇪 Irish",
    voices: [
      { id: "ie_male", label: "Connor", desc: "Male" },
    ],
  },
];

export interface GenerateOptions {
  topic: string;
  length: string;
  aspect_ratio: string;
  voice: string;
  fps: number;
}

interface GenerateFormProps {
  onSubmit: (opts: GenerateOptions) => void;
  isGenerating: boolean;
}

const labelStyle: React.CSSProperties = {
  display: "block",
  fontSize: "0.72rem",
  letterSpacing: "0.14em",
  color: "var(--text-muted)",
  textTransform: "uppercase",
  marginBottom: 10,
};

export default function GenerateForm({ onSubmit, isGenerating }: GenerateFormProps) {
  const [topic,       setTopic]       = useState("");
  const [length,      setLength]      = useState<"short" | "medium">("short");
  const [aspectRatio, setAspectRatio] = useState("9:16");
  const [voice,       setVoice]       = useState("gb_male_rich");  // Ryan — deep British
  const [voiceOpen,   setVoiceOpen]   = useState(false);

  // Find currently selected voice label
  const selectedVoice = VOICE_GROUPS
    .flatMap(g => g.voices)
    .find(v => v.id === voice) ?? { label: "Ryan", desc: "Rich • British Male" };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!topic.trim()) return;
    onSubmit({ topic: topic.trim(), length, aspect_ratio: aspectRatio, voice, fps: 30 });
  };

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
          color: "var(--gold-primary)",
          marginBottom: 10,
        }}>
          Stoic Topic or Concept
        </label>
        <input
          id="topic-input"
          className="input-field"
          type="text"
          value={topic}
          onChange={e => setTopic(e.target.value)}
          placeholder="e.g. Overcoming Fear through Stoicism..."
          maxLength={150}
          disabled={isGenerating}
          required
        />
        <p style={{ fontSize: "0.78rem", color: "var(--text-muted)", marginTop: 8 }}>
          The AI writes a cinematic spoken-word narrative — no philosopher names, no commas
        </p>
      </div>

      {/* ── Quick Topics ── */}
      <div>
        <p style={{ fontSize: "0.72rem", color: "var(--text-muted)", marginBottom: 10, letterSpacing: "0.1em" }}>
          QUICK SELECT
        </p>
        <div style={{ display: "flex", flexWrap: "wrap", gap: 7 }}>
          {STOIC_TOPICS.map(t => (
            <button
              key={t}
              type="button"
              className="topic-chip"
              onClick={() => setTopic(t)}
              disabled={isGenerating}
            >
              {t}
            </button>
          ))}
        </div>
      </div>

      {/* ── Length & Ratio ── */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
        <div>
          <label style={labelStyle}>Video Length</label>
          <div style={{ display: "flex", gap: 8 }}>
            {[["short", "~35s"], ["medium", "~60s"]].map(([val, lbl]) => (
              <button
                key={val}
                type="button"
                id={`length-${val}`}
                className={`option-btn ${length === val ? "selected" : ""}`}
                onClick={() => setLength(val as "short" | "medium")}
                disabled={isGenerating}
                style={{ flex: 1 }}
              >
                {lbl}
              </button>
            ))}
          </div>
        </div>
        <div>
          <label style={labelStyle}>Aspect Ratio</label>
          <div style={{ display: "flex", gap: 8 }}>
            {["9:16", "16:9", "1:1"].map(r => (
              <button
                key={r}
                type="button"
                id={`ratio-${r.replace(":", "-")}`}
                className={`option-btn ${aspectRatio === r ? "selected" : ""}`}
                onClick={() => setAspectRatio(r)}
                disabled={isGenerating}
                style={{ flex: 1, fontSize: "0.8rem" }}
              >
                {r}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* ── Voice Selector ── */}
      <div>
        <label style={labelStyle}>Narrator Voice · Microsoft Neural TTS</label>

        {/* Current selection display */}
        <button
          type="button"
          id="voice-selector-toggle"
          onClick={() => setVoiceOpen(o => !o)}
          disabled={isGenerating}
          style={{
            width: "100%",
            padding: "12px 16px",
            background: "var(--bg-elevated)",
            border: "1px solid var(--border-gold)",
            borderRadius: "var(--radius-md)",
            color: "var(--text-primary)",
            cursor: "pointer",
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            fontSize: "0.9rem",
            fontWeight: 600,
          }}
        >
          <span>{selectedVoice.label} <span style={{ fontWeight: 400, color: "var(--text-muted)", fontSize: "0.8rem" }}>— {selectedVoice.desc}</span></span>
          <span style={{ fontSize: "0.7rem", color: "var(--gold-primary)", letterSpacing: "0.1em" }}>
            {voiceOpen ? "▲ CLOSE" : "▼ CHANGE"}
          </span>
        </button>

        {/* Dropdown — all 15 voices grouped by region */}
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
                  fontSize: "0.68rem",
                  letterSpacing: "0.12em",
                  color: "var(--gold-dim)",
                  textTransform: "uppercase",
                  background: "var(--bg-glass)",
                }}>
                  {group.region}
                </div>
                <div style={{
                  display: "grid",
                  gridTemplateColumns: "repeat(auto-fill, minmax(140px, 1fr))",
                  gap: 1,
                  background: "var(--border-subtle)",
                }}>
                  {group.voices.map(v => (
                    <button
                      key={v.id}
                      type="button"
                      id={`voice-${v.id}`}
                      onClick={() => { setVoice(v.id); setVoiceOpen(false); }}
                      style={{
                        padding: "10px 12px",
                        background: voice === v.id ? "var(--gold-glow)" : "var(--bg-elevated)",
                        border: "none",
                        borderLeft: voice === v.id ? "2px solid var(--gold-primary)" : "2px solid transparent",
                        cursor: "pointer",
                        textAlign: "left",
                      }}
                    >
                      <span style={{
                        display: "block",
                        fontSize: "0.84rem",
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
        type="submit"
        id="generate-btn"
        className="btn-gold"
        disabled={isGenerating || !topic.trim()}
        style={{ width: "100%", fontSize: "1rem", padding: "18px" }}
      >
        {isGenerating ? (
          <>
            <span style={{
              width: 18, height: 18,
              border: "2px solid rgba(0,0,0,0.3)",
              borderTopColor: "#0d0d12",
              borderRadius: "50%",
              display: "inline-block",
              animation: "spin-slow 0.8s linear infinite",
            }} />
            Generating...
          </>
        ) : (
          <>
            <span>⚡</span>
            Generate Cinematic Video
          </>
        )}
      </button>

      <style>{`@keyframes spin-slow { to { transform: rotate(360deg); } }`}</style>
    </form>
  );
}
