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
  "Seneca on Time",
  "Voluntary Hardship",
  "The Art of Not Reacting",
  "Living in the Present",
  "Virtue Above All",
];

const VOICES = [
  { id: "af_bella", label: "Bella (Female)", desc: "Warm American" },
  { id: "bm_george", label: "George (Male)", desc: "Deep British" },
  { id: "am_adam",  label: "Adam (Male)",  desc: "Confident American" },
  { id: "bf_emma",  label: "Emma (Female)", desc: "Elegant British" },
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

export default function GenerateForm({ onSubmit, isGenerating }: GenerateFormProps) {
  const [topic, setTopic]             = useState("");
  const [length, setLength]           = useState<"short" | "medium">("short");
  const [aspectRatio, setAspectRatio] = useState("9:16");
  const [voice, setVoice]             = useState("af_bella");
  const [showAdvanced, setShowAdvanced] = useState(false);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!topic.trim()) return;
    onSubmit({ topic: topic.trim(), length, aspect_ratio: aspectRatio, voice, fps: 60 });
  };

  return (
    <form onSubmit={handleSubmit} style={{ display: "flex", flexDirection: "column", gap: 28 }}>

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
          Be specific — the AI will craft a cinematic narrative around your topic
        </p>
      </div>

      {/* ── Quick Topics ── */}
      <div>
        <p style={{ fontSize: "0.78rem", color: "var(--text-muted)", marginBottom: 10, letterSpacing: "0.08em" }}>
          QUICK SELECT
        </p>
        <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
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
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 20 }}>
        <div>
          <label style={{ display: "block", fontSize: "0.78rem", letterSpacing: "0.1em", color: "var(--text-muted)", textTransform: "uppercase", marginBottom: 10 }}>
            Video Length
          </label>
          <div style={{ display: "flex", gap: 8 }}>
            {[["short", "~35s"], ["medium", "~60s"]].map(([val, label]) => (
              <button
                key={val}
                type="button"
                id={`length-${val}`}
                className={`option-btn ${length === val ? "selected" : ""}`}
                onClick={() => setLength(val as "short" | "medium")}
                disabled={isGenerating}
                style={{ flex: 1 }}
              >
                {label}
              </button>
            ))}
          </div>
        </div>
        <div>
          <label style={{ display: "block", fontSize: "0.78rem", letterSpacing: "0.1em", color: "var(--text-muted)", textTransform: "uppercase", marginBottom: 10 }}>
            Aspect Ratio
          </label>
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

      {/* ── Voice Selection ── */}
      <div>
        <label style={{ display: "block", fontSize: "0.78rem", letterSpacing: "0.1em", color: "var(--text-muted)", textTransform: "uppercase", marginBottom: 10 }}>
          Narrator Voice (Kokoro-82M)
        </label>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(2, 1fr)", gap: 8 }}>
          {VOICES.map(v => (
            <button
              key={v.id}
              type="button"
              id={`voice-${v.id}`}
              className={`option-btn ${voice === v.id ? "selected" : ""}`}
              onClick={() => setVoice(v.id)}
              disabled={isGenerating}
              style={{ textAlign: "left", padding: "10px 14px" }}
            >
              <span style={{ display: "block", fontWeight: 600, fontSize: "0.85rem" }}>{v.label}</span>
              <span style={{ display: "block", fontSize: "0.75rem", opacity: 0.7 }}>{v.desc}</span>
            </button>
          ))}
        </div>
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
