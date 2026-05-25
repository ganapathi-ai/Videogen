"use client";

export interface ProgressState {
  state: "idle" | "running" | "done" | "error" | "closed";
  step: number;
  total: number;
  status: string;
  video_url?: string;
  captions_url?: string;
  timeline_url?: string;
}

const PIPELINE_STEPS = [
  { emoji: "✍️",  label: "Generating Stoic Script",          hint: "Gemini AI crafts your narrative"         },
  { emoji: "🎙️",  label: "Synthesizing Voice",               hint: "Kokoro-82M offline TTS"                  },
  { emoji: "🔬",  label: "Forcing Alignment",                hint: "WhisperX word-level timestamps"           },
  { emoji: "📐",  label: "Assembling Master Timeline",        hint: "Audio is the source of truth"            },
  { emoji: "🎬",  label: "Fetching Cinematic Footage",        hint: "Pexels + Pixabay + FAISS matching"       },
  { emoji: "🎞️",  label: "Compositing Video (Ken Burns)",     hint: "PIL LANCZOS jitter-free zoom"            },
  { emoji: "💬",  label: "Generating Karaoke Subtitles",      hint: "Word-level ASS captions (pysubs2)"       },
  { emoji: "🎵",  label: "Mixing Audio",                      hint: "Emotion-based BGM ducking"               },
  { emoji: "🚀",  label: "Final Render + Validation",         hint: "FFmpeg H.264 + quality gates"            },
];

interface ProgressBarProps {
  progress: ProgressState;
  accentColor?: string;
}

export default function ProgressBar({ progress, accentColor }: ProgressBarProps) {
  const accent = accentColor || "#C4A064";
  const { state, step, total, status } = progress;
  const pct = total > 0 ? Math.round((step / total) * 100) : 0;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 24 }}>

      {/* ── Header ── */}
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
        <div>
          <h3 style={{
            fontFamily: "'Cinzel', serif",
            fontSize: "1rem",
          color: state === "error" ? "var(--red-fail)" : accent,
          letterSpacing: "0.08em",
          transition: "color 0.4s ease",
          }}>
            {state === "running" ? "Pipeline Active" :
             state === "done"    ? "✓ Complete" :
             state === "error"   ? "✗ Failed" : "Preparing..."}
          </h3>
          <p style={{ fontSize: "0.82rem", color: "var(--text-secondary)", marginTop: 4 }}>
            {status}
          </p>
        </div>

        {/* Waveform when running */}
        {state === "running" && (
          <div className="waveform" aria-hidden="true">
            {Array.from({ length: 12 }, (_, i) => (
              <div key={i} className="wave-bar" />
            ))}
          </div>
        )}

        {/* Percentage badge */}
        {state === "running" && (
          <div style={{
            fontFamily: "'Cinzel', serif",
            fontSize: "1.5rem",
            fontWeight: 700,
            color: accent,
            transition: "color 0.4s ease",
          }}>
            {pct}%
          </div>
        )}
      </div>

      {/* ── Progress Track ── */}
      <div className="progress-track">
        <div
          className="progress-fill"
          role="progressbar"
          aria-valuenow={pct}
          aria-valuemin={0}
          aria-valuemax={100}
          style={{ width: `${pct}%` }}
        />
      </div>

      {/* ── Pipeline Steps ── */}
      <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
        {PIPELINE_STEPS.map((s, i) => {
          const stepNum = i + 1;
          const isDone   = step > stepNum;
          const isActive = step === stepNum;

          return (
            <div
              key={i}
              id={`step-${stepNum}`}
              className={`progress-step ${isActive ? "active" : ""} ${isDone ? "done" : ""}`}
            >
              <div className="step-icon">
                {isDone ? "✓" : s.emoji}
              </div>
              <div style={{ flex: 1 }}>
                <div style={{
                  fontSize: "0.875rem",
                  fontWeight: isActive ? 600 : 400,
                  color: isActive ? "var(--text-primary)" : "inherit",
                }}>
                  {s.label}
                </div>
                {isActive && (
                  <div style={{ fontSize: "0.75rem", color: accent, opacity: 0.7, marginTop: 2 }}>
                    {s.hint}
                  </div>
                )}
              </div>

              {/* Active spinner */}
              {isActive && (
                <div style={{
                  width: 16, height: 16,
                  border: "2px solid var(--border-subtle)",
                  borderTopColor: accent,
                  borderRadius: "50%",
                  animation: "spin-slow 0.8s linear infinite",
                  flexShrink: 0,
                }} />
              )}
            </div>
          );
        })}
      </div>

      <style>{`@keyframes spin-slow { to { transform: rotate(360deg); } }`}</style>
    </div>
  );
}
