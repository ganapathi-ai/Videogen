"use client";

import { useState, useEffect, useCallback } from "react";
import GenerateForm, { type GenerateOptions } from "./components/GenerateForm";
import ProgressBar, { type ProgressState }   from "./components/ProgressBar";
import ResultCard                             from "./components/ResultCard";

const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8000";

type AppState = "idle" | "generating" | "done" | "error";

export interface ChannelInfo {
  id: string;
  name: string;
  handle: string;
  tagline: string;
  description: string;
  emoji: string;
  accent_color: string;
  topics: string[];
  seo_tags: string[];
  default_voice: string;
  default_aspect: string;
  default_length: string;
}

// ── Hardcoded fallback channels (if backend /api/channels unreachable)
const DEFAULT_CHANNELS: ChannelInfo[] = [
  {
    id: "stoic",
    name: "The Inner Citadel",
    handle: "@TheInnerCitadel",
    tagline: "Ancient Wisdom. Modern Clarity.",
    description: "Stoic philosophy for daily life — discipline, resilience, mindset.",
    emoji: "🏛️",
    accent_color: "#C4A064",
    default_voice: "gb_ryan",
    default_aspect: "9:16",
    default_length: "short",
    seo_tags: ["stoicism", "philosophy", "discipline", "mindset"],
    topics: [
      "Overcoming Fear Through Stoicism", "The Obstacle is the Way",
      "Ego is the Enemy", "Discipline is Freedom", "Memento Mori",
      "Amor Fati — Love Your Fate", "The Dichotomy of Control",
      "Stillness is the Key", "Why Stoics Never Complain",
      "The Art of Not Reacting",
    ],
  },
  {
    id: "tech",
    name: "neuralbaba_empire",
    handle: "@neuralbaba_empire",
    tagline: "The Future is Already Here.",
    description: "AI, technology and data science — explained for everyone.",
    emoji: "💻",
    accent_color: "#00D4FF",
    default_voice: "us_christopher",
    default_aspect: "9:16",
    default_length: "short",
    seo_tags: ["AI", "machine learning", "tech", "programming"],
    topics: [
      "AI is Changing Everything Right Now", "How ChatGPT Actually Works Inside",
      "Why Python Won the Data Science War", "The Rise of AI Agents",
      "Why 90 Percent of AI Projects Fail", "How Netflix Recommends Your Next Show",
      "The Truth About AI Consciousness", "The Future of Work in the Age of AI",
      "The Mindset of a 10x Engineer", "The Dark Side of Social Media Algorithms",
    ],
  },
];

export default function HomePage() {
  const [appState, setAppState]     = useState<AppState>("idle");
  const [taskId, setTaskId]         = useState<string | null>(null);
  const [progress, setProgress]     = useState<ProgressState>({
    state: "idle", step: 0, total: 9, status: "",
  });
  const [result, setResult]         = useState<{
    video_url: string; captions_url: string; timeline_url: string;
    title: string; duration: number;
  } | null>(null);
  const [error, setError]           = useState<string | null>(null);
  const [channels, setChannels]     = useState<ChannelInfo[]>(DEFAULT_CHANNELS);
  const [activeChannel, setActiveChannel] = useState<ChannelInfo>(DEFAULT_CHANNELS[0]);

  // ── Load channels from backend ───────────────────────────────
  useEffect(() => {
    fetch(`${BACKEND_URL}/api/channels`)
      .then(r => r.json())
      .then(data => {
        if (data.channels?.length) {
          setChannels(data.channels);
          setActiveChannel(data.channels[0]);
        }
      })
      .catch(() => { /* use defaults */ });
  }, []);

  // ── SSE Progress Stream ──────────────────────────────────────
  const startSSEStream = useCallback((tid: string) => {
    const evtSource = new EventSource(`${BACKEND_URL}/api/stream-progress/${tid}`);
    evtSource.onmessage = (e) => {
      try {
        const data = JSON.parse(e.data);
        setProgress({
          state: data.state || "running", step: data.step ?? 0,
          total: data.total ?? 9, status: data.status || "",
          video_url: data.video_url, captions_url: data.captions_url,
          timeline_url: data.timeline_url,
        });
        if (data.state === "done") {
          evtSource.close();
          setResult({
            video_url: data.video_url || "", captions_url: data.captions_url || "",
            timeline_url: data.timeline_url || "",
            title: data.title || activeChannel.name,
            duration: data.duration || 0,
          });
          setAppState("done");
        } else if (data.state === "error" || data.state === "closed") {
          evtSource.close();
          setError(data.status || "An unknown error occurred.");
          setAppState("error");
        }
      } catch { /* ignore parse errors */ }
    };
    evtSource.onerror = () => { evtSource.close(); pollFallback(tid); };
    return evtSource;
  }, [activeChannel]);

  const pollFallback = async (tid: string) => {
    let attempts = 0;
    const interval = setInterval(async () => {
      if (++attempts > 600) { clearInterval(interval); return; }
      try {
        const r = await fetch(`${BACKEND_URL}/api/status/${tid}`);
        const data = await r.json();
        if (data.status === "done") {
          clearInterval(interval);
          const rd = await (await fetch(`${BACKEND_URL}/api/result/${tid}`)).json();
          setResult({
            video_url: rd.video_url || "", captions_url: rd.captions_url || "",
            timeline_url: rd.timeline_url || "",
            title: rd.title || activeChannel.name, duration: rd.duration || 0,
          });
          setAppState("done");
        } else if (data.status === "failed") {
          clearInterval(interval);
          setError(data.error || "Pipeline failed.");
          setAppState("error");
        } else {
          setProgress(p => ({ ...p, status: data.message || "Processing..." }));
        }
      } catch { /* continue polling */ }
    }, 2000);
  };

  // ── Submit Handler ───────────────────────────────────────────
  const handleGenerate = async (opts: GenerateOptions) => {
    setError(null); setResult(null);
    setAppState("generating");
    setProgress({ state: "running", step: 0, total: 9, status: "Sending to pipeline..." });
    try {
      const resp = await fetch(`${BACKEND_URL}/api/generate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ...opts, channel: activeChannel.id }),
      });
      if (!resp.ok) {
        const err = await resp.json();
        throw new Error(err.detail || "Failed to start generation");
      }
      const { job_id } = await resp.json();
      setTaskId(job_id);
      startSSEStream(job_id);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Connection failed");
      setAppState("error");
    }
  };

  const handleReset = () => {
    setAppState("idle"); setTaskId(null);
    setProgress({ state: "idle", step: 0, total: 9, status: "" });
    setResult(null); setError(null);
  };

  // ── Channel accent vars ──────────────────────────────────────
  const accent     = activeChannel.accent_color;
  const isTech     = activeChannel.id === "tech";
  const accentGlow = isTech
    ? "rgba(0,212,255,0.08)"
    : "rgba(196,160,100,0.08)";
  const accentBorder = isTech
    ? "rgba(0,212,255,0.25)"
    : "rgba(196,160,100,0.25)";

  // ── Render ────────────────────────────────────────────────────
  return (
    <>
      {/* ── Ambient Orbs (color shifts per channel) ── */}
      <div className="orb" style={{
        width: 600, height: 600,
        background: `radial-gradient(circle, ${accent}18 0%, transparent 70%)`,
        top: "-15%", left: "50%", transform: "translateX(-50%)",
        position: "fixed", pointerEvents: "none", zIndex: 0,
        transition: "background 0.6s ease",
      }} aria-hidden />
      <div className="orb orb-blue" style={{
        background: `radial-gradient(circle, ${accent}12 0%, transparent 70%)`,
        bottom: "10%", right: "5%",
        transition: "background 0.6s ease",
      }} aria-hidden />

      <main style={{ minHeight: "100vh", position: "relative", zIndex: 1 }}>

        {/* ── Header ─────────────────────────────────────────────── */}
        <header style={{ paddingTop: 64, paddingBottom: 32, textAlign: "center" }}>
          <div className="container">

            {/* Platform badge */}
            <div style={{
              display: "inline-flex", alignItems: "center", gap: 8,
              padding: "5px 16px",
              border: `1px solid ${accentBorder}`,
              borderRadius: 50, marginBottom: 32,
              fontSize: "0.70rem", letterSpacing: "0.18em",
              color: accent, textTransform: "uppercase",
              background: accentGlow,
              transition: "all 0.4s ease",
            }}>
              <span>⚡</span> NeuralBaba Empire · Autonomous Video Pipeline
            </div>

            {/* ── Channel Selector Tabs ── */}
            <div style={{
              display: "inline-flex",
              gap: 4,
              padding: 4,
              background: "rgba(255,255,255,0.04)",
              border: "1px solid rgba(255,255,255,0.08)",
              borderRadius: 16,
              marginBottom: 32,
            }}>
              {channels.map(ch => {
                const isActive = ch.id === activeChannel.id;
                const chAccent = ch.accent_color;
                return (
                  <button
                    key={ch.id}
                    id={`channel-tab-${ch.id}`}
                    onClick={() => {
                      if (appState === "idle") setActiveChannel(ch);
                    }}
                    disabled={appState !== "idle"}
                    style={{
                      display: "flex", alignItems: "center", gap: 10,
                      padding: "12px 24px",
                      borderRadius: 12,
                      border: isActive
                        ? `1px solid ${chAccent}50`
                        : "1px solid transparent",
                      background: isActive
                        ? `linear-gradient(135deg, ${chAccent}18, ${chAccent}08)`
                        : "transparent",
                      cursor: appState !== "idle" ? "not-allowed" : "pointer",
                      transition: "all 0.3s ease",
                      opacity: appState !== "idle" && !isActive ? 0.4 : 1,
                    }}
                  >
                    <span style={{ fontSize: "1.3rem" }}>{ch.emoji}</span>
                    <div style={{ textAlign: "left" }}>
                      <div style={{
                        fontSize: "0.88rem",
                        fontWeight: 700,
                        color: isActive ? chAccent : "var(--text-secondary)",
                        transition: "color 0.3s ease",
                        letterSpacing: "0.01em",
                      }}>
                        {ch.name}
                      </div>
                      <div style={{
                        fontSize: "0.68rem",
                        color: isActive ? `${chAccent}cc` : "var(--text-muted)",
                        letterSpacing: "0.05em",
                        transition: "color 0.3s ease",
                      }}>
                        {ch.handle}
                      </div>
                    </div>
                    {isActive && (
                      <div style={{
                        width: 6, height: 6, borderRadius: "50%",
                        background: chAccent,
                        boxShadow: `0 0 8px ${chAccent}`,
                        animation: "pulse 2s infinite",
                      }} />
                    )}
                  </button>
                );
              })}
            </div>

            {/* Channel tagline */}
            <div style={{ marginBottom: 8 }}>
              <span style={{
                fontSize: "clamp(0.8rem, 1.5vw, 1rem)",
                color: "var(--text-secondary)",
                letterSpacing: "0.06em",
                transition: "all 0.4s ease",
              }}>
                {activeChannel.tagline}
              </span>
            </div>

            {/* Channel description */}
            <p style={{
              fontSize: "0.82rem",
              color: "var(--text-muted)",
              maxWidth: 480,
              margin: "0 auto 28px",
              lineHeight: 1.6,
            }}>
              {activeChannel.description}
            </p>

            {/* Watermark preview badge */}
            <div style={{
              display: "inline-flex", alignItems: "center", gap: 6,
              padding: "4px 12px",
              border: `1px solid ${accentBorder}`,
              borderRadius: 6,
              fontSize: "0.68rem",
              color: `${accent}99`,
              background: accentGlow,
              letterSpacing: "0.05em",
              marginBottom: 8,
            }}>
              <span style={{ opacity: 0.6 }}>🔖</span>
              Watermark: <strong style={{ color: accent, opacity: 0.7 }}>
                {activeChannel.name}
              </strong>
            </div>

            {/* Feature pills */}
            <div style={{
              display: "flex", flexWrap: "wrap",
              justifyContent: "center", gap: 8, marginTop: 20,
            }}>
              {[
                "Groq AI Script", "Edge-TTS Voice", "WhisperX Align",
                "Ken Burns Video", "Karaoke Subtitles", "Transparent Watermark",
              ].map(f => (
                <span key={f} style={{
                  padding: "4px 12px",
                  background: "var(--bg-glass)",
                  border: "1px solid var(--border-subtle)",
                  borderRadius: 50,
                  fontSize: "0.72rem",
                  color: "var(--text-secondary)",
                }}>
                  {f}
                </span>
              ))}
            </div>
          </div>
        </header>

        {/* ── Gold/Cyan Divider (color per channel) ── */}
        <div className="container">
          <div style={{
            height: 1,
            background: `linear-gradient(to right, transparent, ${accent}40, transparent)`,
            margin: "4px 0 40px",
            transition: "background 0.5s ease",
          }} />
        </div>

        {/* ── Main Content ─────────────────────────────────────── */}
        <section style={{ padding: "0 0 80px" }}>
          <div className="container">
            <div style={{
              display: "grid",
              gridTemplateColumns: "minmax(0,1.1fr) minmax(0,0.9fr)",
              gap: 40, alignItems: "start",
            }}>

              {/* LEFT: Form or Result */}
              <div>
                {appState === "done" && result ? (
                  <ResultCard
                    videoUrl={result.video_url}
                    captionsUrl={result.captions_url}
                    timelineUrl={result.timeline_url}
                    title={result.title}
                    duration={result.duration}
                    onReset={handleReset}
                  />
                ) : (
                  <div className="glass-card" style={{ padding: 36 }}>
                    <div style={{ marginBottom: 24 }}>
                      <h2 style={{
                        fontFamily: "'Cinzel', serif",
                        fontSize: "1.05rem",
                        letterSpacing: "0.08em",
                        color: accent,
                        marginBottom: 6,
                        transition: "color 0.4s ease",
                      }}>
                        {activeChannel.emoji} Configure {activeChannel.name} Video
                      </h2>
                      <p style={{ fontSize: "0.80rem", color: "var(--text-muted)" }}>
                        Channel: <strong style={{ color: `${accent}cc` }}>
                          {activeChannel.handle}
                        </strong>
                        {" · "}Watermark burned on render
                      </p>
                    </div>

                    <GenerateForm
                      onSubmit={handleGenerate}
                      isGenerating={appState === "generating"}
                      channel={activeChannel}
                      accentColor={accent}
                    />

                    {appState === "error" && error && (
                      <div style={{
                        marginTop: 20, padding: "14px 18px",
                        background: "rgba(239,68,68,0.08)",
                        border: "1px solid rgba(239,68,68,0.25)",
                        borderRadius: "var(--radius-md)",
                        fontSize: "0.85rem", color: "var(--red-fail)",
                      }}>
                        <strong>Error:</strong> {error}
                        <br />
                        <span style={{ fontSize: "0.78rem", opacity: 0.8 }}>
                          Make sure the backend is running on {BACKEND_URL}
                        </span>
                      </div>
                    )}
                  </div>
                )}
              </div>

              {/* RIGHT: Progress / Info Panel */}
              <div style={{ display: "flex", flexDirection: "column", gap: 24 }}>

                {appState === "generating" && (
                  <div className="glass-card" style={{ padding: 32 }}>
                    <h2 style={{
                      fontFamily: "'Cinzel', serif",
                      fontSize: "0.88rem",
                      letterSpacing: "0.12em",
                      color: accent,
                      textTransform: "uppercase",
                      marginBottom: 24,
                      transition: "color 0.4s ease",
                    }}>
                      Pipeline Progress
                    </h2>
                    <ProgressBar progress={progress} accentColor={accent} />
                  </div>
                )}

                {appState === "idle" && (
                  <>
                    {/* Pipeline steps */}
                    <div className="glass-card" style={{ padding: 28 }}>
                      <h3 style={{
                        fontFamily: "'Cinzel', serif",
                        fontSize: "0.82rem",
                        letterSpacing: "0.12em",
                        color: accent,
                        textTransform: "uppercase",
                        marginBottom: 18,
                        transition: "color 0.4s ease",
                      }}>
                        9-Step Autonomous Pipeline
                      </h3>
                      <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
                        {[
                          { n: "1", label: "Script",     desc: "Groq AI → channel-specific narrative" },
                          { n: "2", label: "Voice",      desc: "Edge-TTS deep voice synthesis" },
                          { n: "3", label: "Align",      desc: "WhisperX word-level timestamps" },
                          { n: "4", label: "Timeline",   desc: "Master sync document assembled" },
                          { n: "5", label: "Footage",    desc: "Pexels/Pixabay + FAISS matching" },
                          { n: "6", label: "Video",      desc: "PIL LANCZOS Ken Burns composite" },
                          { n: "7", label: "Captions",   desc: "pysubs2 ASS karaoke subtitles" },
                          { n: "8", label: "Audio Mix",  desc: "Emotion-based BGM ducking" },
                          { n: "9", label: "Render",     desc: `FFmpeg + ${activeChannel.name} watermark` },
                        ].map(s => (
                          <div key={s.n} style={{ display: "flex", alignItems: "center", gap: 12 }}>
                            <div style={{
                              width: 26, height: 26, borderRadius: "50%",
                              background: `${accent}15`,
                              border: `1px solid ${accent}40`,
                              display: "flex", alignItems: "center", justifyContent: "center",
                              fontSize: "0.70rem", color: accent, fontWeight: 700,
                              flexShrink: 0, transition: "all 0.4s ease",
                            }}>
                              {s.n}
                            </div>
                            <div>
                              <span style={{ fontSize: "0.80rem", color: "var(--text-primary)", fontWeight: 600 }}>
                                {s.label}
                              </span>
                              <span style={{ fontSize: "0.75rem", color: "var(--text-muted)", marginLeft: 8 }}>
                                {s.desc}
                              </span>
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>

                    {/* Channel SEO Tags */}
                    <div className="glass-card" style={{ padding: "20px 24px" }}>
                      <h3 style={{
                        fontFamily: "'Cinzel', serif",
                        fontSize: "0.72rem",
                        letterSpacing: "0.15em",
                        color: "var(--text-muted)",
                        textTransform: "uppercase",
                        marginBottom: 12,
                      }}>
                        SEO Tags · {activeChannel.name}
                      </h3>
                      <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
                        {activeChannel.seo_tags.slice(0, 12).map(tag => (
                          <span key={tag} style={{
                            padding: "3px 10px",
                            background: `${accent}10`,
                            border: `1px solid ${accent}25`,
                            borderRadius: 50,
                            fontSize: "0.68rem",
                            color: `${accent}cc`,
                            transition: "all 0.4s ease",
                          }}>
                            #{tag}
                          </span>
                        ))}
                      </div>
                    </div>
                  </>
                )}

                {/* Cost counter */}
                <div style={{
                  padding: "16px 24px",
                  border: `1px solid ${accentBorder}`,
                  borderRadius: "var(--radius-md)",
                  background: accentGlow,
                  textAlign: "center",
                  transition: "all 0.4s ease",
                }}>
                  <div style={{
                    fontSize: "2rem", fontWeight: 900, color: accent,
                    fontFamily: "'Cinzel', serif",
                    transition: "color 0.4s ease",
                  }}>
                    $0.00
                  </div>
                  <div style={{ fontSize: "0.78rem", color: "var(--text-secondary)", marginTop: 4 }}>
                    Per video generated · Forever free
                  </div>
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* ── Footer ───────────────────────────────────────────── */}
        <footer style={{
          borderTop: "1px solid var(--border-subtle)",
          padding: "24px 0", textAlign: "center",
        }}>
          <div className="container">
            <p style={{ fontSize: "0.78rem", color: "var(--text-muted)" }}>
              <strong style={{ color: accent }}>NeuralBaba Empire</strong>
              {" · "}The Inner Citadel &amp; neuralbaba_empire{" · "}
              <span style={{ color: "var(--text-muted)", opacity: 0.7 }}>
                Autonomous Video Pipeline · 100% Free · Open Source
              </span>
            </p>
          </div>
        </footer>
      </main>

      <style>{`
        @keyframes pulse {
          0%, 100% { opacity: 1; transform: scale(1); }
          50% { opacity: 0.6; transform: scale(0.85); }
        }
        @media (max-width: 768px) {
          section > div.container > div {
            grid-template-columns: 1fr !important;
          }
        }
      `}</style>
    </>
  );
}
