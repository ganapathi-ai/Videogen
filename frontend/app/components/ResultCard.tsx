"use client";

interface ResultCardProps {
  videoUrl:    string;
  captionsUrl: string;
  timelineUrl: string;
  title:       string;
  duration:    number;
  onReset:     () => void;
}

export default function ResultCard({
  videoUrl, captionsUrl, timelineUrl, title, duration, onReset
}: ResultCardProps) {

  const durationStr = duration > 0
    ? `${Math.floor(duration / 60)}:${String(Math.round(duration % 60)).padStart(2, "0")}`
    : "—";

  return (
    <div className="result-card animate-fadeIn">

      {/* ── Top Banner ── */}
      <div style={{
        background: "linear-gradient(135deg, rgba(201,168,76,0.15), rgba(201,168,76,0.05))",
        borderBottom: "1px solid var(--border-gold)",
        padding: "28px 32px",
      }}>
        <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
          {/* Animated checkmark */}
          <div style={{
            width: 52, height: 52,
            borderRadius: "50%",
            background: "linear-gradient(135deg, var(--gold-primary), var(--gold-dim))",
            display: "flex", alignItems: "center", justifyContent: "center",
            fontSize: "1.5rem",
            boxShadow: "0 0 30px rgba(201,168,76,0.4)",
          }}>
            ✓
          </div>
          <div>
            <p style={{
              fontFamily: "'Cinzel', serif",
              fontSize: "0.7rem",
              letterSpacing: "0.2em",
              color: "var(--gold-primary)",
              textTransform: "uppercase",
              marginBottom: 4,
            }}>
              Video Ready
            </p>
            <h2 style={{
              fontFamily: "'Cinzel', serif",
              fontSize: "1.1rem",
              color: "var(--text-primary)",
              lineHeight: 1.3,
            }}>
              {title}
            </h2>
          </div>
        </div>

        {/* Meta row */}
        <div style={{ display: "flex", gap: 24, marginTop: 20 }}>
          {[
            { label: "Duration", value: durationStr },
            { label: "Format",   value: "H.264 MP4" },
            { label: "Quality",  value: "8 Mbps"    },
            { label: "FPS",      value: "60"         },
          ].map(m => (
            <div key={m.label}>
              <div style={{ fontSize: "0.7rem", color: "var(--text-muted)", letterSpacing: "0.1em", textTransform: "uppercase" }}>
                {m.label}
              </div>
              <div style={{ fontSize: "0.9rem", color: "var(--text-primary)", fontWeight: 600, marginTop: 2 }}>
                {m.value}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* ── Download Section ── */}
      <div style={{ padding: "28px 32px", display: "flex", flexDirection: "column", gap: 16 }}>

        <p style={{
          fontFamily: "'Cinzel', serif",
          fontSize: "0.7rem",
          letterSpacing: "0.15em",
          color: "var(--text-muted)",
          textTransform: "uppercase",
          marginBottom: 4,
        }}>
          Download Files
        </p>

        {/* Primary — Video */}
        <a
          id="download-video"
          href={videoUrl}
          download
          className="download-btn primary"
          target="_blank"
          rel="noopener noreferrer"
        >
          <span style={{ fontSize: "1.2rem" }}>🎬</span>
          <div>
            <div style={{ fontWeight: 700 }}>Download Video (MP4)</div>
            <div style={{ fontSize: "0.75rem", opacity: 0.8 }}>final_video.mp4 · H.264 · 8Mbps · 60fps</div>
          </div>
        </a>

        {/* Secondary downloads */}
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
          <a
            id="download-captions"
            href={captionsUrl}
            download
            className="download-btn secondary"
            target="_blank"
            rel="noopener noreferrer"
          >
            <span>💬</span>
            <div>
              <div style={{ fontWeight: 600 }}>Captions</div>
              <div style={{ fontSize: "0.72rem" }}>captions.ass</div>
            </div>
          </a>
          <a
            id="download-timeline"
            href={timelineUrl}
            download
            className="download-btn secondary"
            target="_blank"
            rel="noopener noreferrer"
          >
            <span>📐</span>
            <div>
              <div style={{ fontWeight: 600 }}>Timeline</div>
              <div style={{ fontSize: "0.72rem" }}>timeline.json</div>
            </div>
          </a>
        </div>
      </div>

      {/* ── Footer Actions ── */}
      <div style={{
        padding: "20px 32px",
        borderTop: "1px solid var(--border-subtle)",
        display: "flex",
        justifyContent: "space-between",
        alignItems: "center",
      }}>
        <p style={{ fontSize: "0.8rem", color: "var(--text-muted)" }}>
          Generated with 100% open-source tools · No API costs
        </p>
        <button
          id="generate-another-btn"
          onClick={onReset}
          className="btn-ghost"
        >
          ↩ Generate Another
        </button>
      </div>
    </div>
  );
}
