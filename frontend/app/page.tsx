"use client";

import { useState, useEffect, useCallback } from "react";
import GenerateForm, { type GenerateOptions } from "./components/GenerateForm";
import ProgressBar, { type ProgressState }   from "./components/ProgressBar";
import ResultCard                             from "./components/ResultCard";

const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8000";

type AppState = "idle" | "generating" | "done" | "error";

export default function HomePage() {
  const [appState, setAppState]   = useState<AppState>("idle");
  const [taskId,   setTaskId]     = useState<string | null>(null);
  const [progress, setProgress]   = useState<ProgressState>({
    state: "idle", step: 0, total: 9, status: "",
  });
  const [result, setResult]       = useState<{
    video_url: string; captions_url: string; timeline_url: string;
    title: string; duration: number;
  } | null>(null);
  const [error, setError]         = useState<string | null>(null);

  // ── SSE Progress Stream ────────────────────────────────────
  const startSSEStream = useCallback((tid: string) => {
    const url = `${BACKEND_URL}/api/stream-progress/${tid}`;
    const evtSource = new EventSource(url);

    evtSource.onmessage = (e) => {
      try {
        const data = JSON.parse(e.data);
        const newProgress: ProgressState = {
          state:        data.state || "running",
          step:         data.step  ?? 0,
          total:        data.total ?? 9,
          status:       data.status || "",
          video_url:    data.video_url,
          captions_url: data.captions_url,
          timeline_url: data.timeline_url,
        };
        setProgress(newProgress);

        if (data.state === "done") {
          evtSource.close();
          setResult({
            video_url:    data.video_url    || "",
            captions_url: data.captions_url || "",
            timeline_url: data.timeline_url || "",
            title:        data.title        || "Inner Citadel Video",
            duration:     data.duration     || 0,
          });
          setAppState("done");
        } else if (data.state === "error" || data.state === "closed") {
          evtSource.close();
          setError(data.status || "An unknown error occurred.");
          setAppState("error");
        }
      } catch {
        // ignore parse errors
      }
    };

    evtSource.onerror = () => {
      evtSource.close();
      // Fallback: poll the status endpoint
      pollFallback(tid);
    };

    return evtSource;
  }, []);

  // ── Polling Fallback (if SSE fails) ───────────────────────
  const pollFallback = async (tid: string) => {
    let attempts = 0;
    const interval = setInterval(async () => {
      attempts++;
      if (attempts > 600) { clearInterval(interval); return; } // 10 min max

      try {
        const r = await fetch(`${BACKEND_URL}/api/status/${tid}`);
        const data = await r.json();

        if (data.status === "done") {
          clearInterval(interval);
          const res = await fetch(`${BACKEND_URL}/api/result/${tid}`);
          const rd  = await res.json();
          setResult({
            video_url:    rd.video_url    || "",
            captions_url: rd.captions_url || "",
            timeline_url: rd.timeline_url || "",
            title:        rd.title        || "Inner Citadel",
            duration:     rd.duration     || 0,
          });
          setAppState("done");
        } else if (data.status === "failed") {
          clearInterval(interval);
          setError(data.error || "Pipeline failed.");
          setAppState("error");
        } else {
          setProgress(p => ({ ...p, status: data.message || "Processing..." }));
        }
      } catch {
        // continue polling
      }
    }, 2000);
  };

  // ── Submit Handler ─────────────────────────────────────────
  const handleGenerate = async (opts: GenerateOptions) => {
    setError(null);
    setResult(null);
    setAppState("generating");
    setProgress({ state: "running", step: 0, total: 9, status: "Sending request to pipeline..." });

    try {
      const resp = await fetch(`${BACKEND_URL}/api/generate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(opts),
      });

      if (!resp.ok) {
        const err = await resp.json();
        throw new Error(err.detail || "Failed to start generation");
      }

      const { job_id } = await resp.json();   // backend returns job_id
      setTaskId(job_id);
      startSSEStream(job_id);

    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Connection failed";
      setError(msg);
      setAppState("error");
    }
  };

  const handleReset = () => {
    setAppState("idle");
    setTaskId(null);
    setProgress({ state: "idle", step: 0, total: 9, status: "" });
    setResult(null);
    setError(null);
  };

  // ── Render ─────────────────────────────────────────────────
  return (
    <>
      {/* ── Ambient Orbs ── */}
      <div className="orb orb-gold" style={{ top: "-10%", left: "50%", transform: "translateX(-50%)" }} aria-hidden />
      <div className="orb orb-blue" style={{ bottom: "10%", right: "5%" }} aria-hidden />

      <main style={{ minHeight: "100vh", position: "relative", zIndex: 1 }}>

        {/* ── Header / Hero ── */}
        <header style={{ paddingTop: "72px", paddingBottom: "48px", textAlign: "center" }}>
          <div className="container">

            {/* Channel badge */}
            <div style={{
              display: "inline-flex",
              alignItems: "center",
              gap: 8,
              padding: "6px 18px",
              border: "1px solid var(--border-gold)",
              borderRadius: "50px",
              marginBottom: 28,
              fontSize: "0.72rem",
              letterSpacing: "0.18em",
              color: "var(--gold-primary)",
              textTransform: "uppercase",
              background: "var(--gold-glow)",
            }}>
              <span>⚡</span> Autonomous Pipeline · 100% Free · Open Source
            </div>

            {/* Main title */}
            <h1 style={{
              fontFamily: "'Cinzel', serif",
              fontSize: "clamp(2.4rem, 5vw, 4.5rem)",
              fontWeight: 900,
              lineHeight: 1.1,
              letterSpacing: "0.06em",
              marginBottom: 20,
            }}>
              <span className="text-gold">THE INNER</span>
              <br />
              <span style={{ color: "var(--text-primary)" }}>CITADEL</span>
            </h1>

            <p style={{
              fontSize: "clamp(1rem, 2vw, 1.2rem)",
              color: "var(--text-secondary)",
              maxWidth: 560,
              margin: "0 auto 16px",
              lineHeight: 1.7,
            }}>
              Generate cinematic Stoic philosophy videos autonomously.
              Script → Voice → Alignment → Footage → Subtitles → Render.
            </p>

            {/* Feature pills */}
            <div style={{ display: "flex", flexWrap: "wrap", justifyContent: "center", gap: 10, marginTop: 24 }}>
              {[
                "Groq AI Script", "Edge-TTS Voice", "WhisperX Align",
                "Ken Burns Video", "Karaoke Subtitles", "60fps H.264",
              ].map(f => (
                <span key={f} style={{
                  padding: "5px 14px",
                  background: "var(--bg-glass)",
                  border: "1px solid var(--border-subtle)",
                  borderRadius: "50px",
                  fontSize: "0.75rem",
                  color: "var(--text-secondary)",
                }}>
                  {f}
                </span>
              ))}
            </div>
          </div>
        </header>

        {/* ── Gold Divider ── */}
        <div className="container">
          <div className="gold-divider" />
        </div>

        {/* ── Main Content ── */}
        <section style={{ padding: "48px 0 80px" }}>
          <div className="container">
            <div style={{
              display: "grid",
              gridTemplateColumns: "minmax(0, 1.1fr) minmax(0, 0.9fr)",
              gap: 40,
              alignItems: "start",
            }}>

              {/* LEFT: Generate Form or Result */}
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
                  <div className="glass-card" style={{ padding: "36px" }}>
                    <div style={{ marginBottom: 28 }}>
                      <h2 style={{
                        fontFamily: "'Cinzel', serif",
                        fontSize: "1.1rem",
                        letterSpacing: "0.08em",
                        color: "var(--text-primary)",
                        marginBottom: 6,
                      }}>
                        Configure Your Video
                      </h2>
                      <p style={{ fontSize: "0.83rem", color: "var(--text-muted)" }}>
                        All fields pre-seeded with optimal Stoic defaults
                      </p>
                    </div>

                    <GenerateForm
                      onSubmit={handleGenerate}
                      isGenerating={appState === "generating"}
                    />

                    {/* Error display */}
                    {appState === "error" && error && (
                      <div style={{
                        marginTop: 20,
                        padding: "14px 18px",
                        background: "rgba(239,68,68,0.08)",
                        border: "1px solid rgba(239,68,68,0.25)",
                        borderRadius: "var(--radius-md)",
                        fontSize: "0.85rem",
                        color: "var(--red-fail)",
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

                {/* Progress Panel (visible during generation) */}
                {(appState === "generating") && (
                  <div className="glass-card" style={{ padding: "32px" }}>
                    <h2 style={{
                      fontFamily: "'Cinzel', serif",
                      fontSize: "0.9rem",
                      letterSpacing: "0.12em",
                      color: "var(--gold-primary)",
                      textTransform: "uppercase",
                      marginBottom: 24,
                    }}>
                      Pipeline Progress
                    </h2>
                    <ProgressBar progress={progress} />
                  </div>
                )}

                {/* Architecture Info Panel */}
                {appState === "idle" && (
                  <div className="glass-card" style={{ padding: "28px" }}>
                    <h3 style={{
                      fontFamily: "'Cinzel', serif",
                      fontSize: "0.85rem",
                      letterSpacing: "0.12em",
                      color: "var(--gold-primary)",
                      textTransform: "uppercase",
                      marginBottom: 20,
                    }}>
                      9-Step Autonomous Pipeline
                    </h3>
                    <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
                      {[
                        { n: "1", label: "Script",     desc: "Gemini AI → Stoic narrative JSON" },
                        { n: "2", label: "Voice",      desc: "Kokoro-82M offline TTS synthesis" },
                        { n: "3", label: "Align",      desc: "WhisperX word-level timestamps"  },
                        { n: "4", label: "Timeline",   desc: "Master sync document assembled"  },
                        { n: "5", label: "Footage",    desc: "Pexels/Pixabay + FAISS matching" },
                        { n: "6", label: "Video",      desc: "PIL LANCZOS Ken Burns composit"  },
                        { n: "7", label: "Captions",   desc: "pysubs2 ASS karaoke subtitles"  },
                        { n: "8", label: "Audio Mix",  desc: "Emotion-based BGM ducking"       },
                        { n: "9", label: "Render",     desc: "FFmpeg H.264 + quality gates"    },
                      ].map(s => (
                        <div key={s.n} style={{ display: "flex", alignItems: "center", gap: 14 }}>
                          <div style={{
                            width: 28, height: 28,
                            borderRadius: "50%",
                            background: "var(--gold-glow)",
                            border: "1px solid var(--border-gold)",
                            display: "flex", alignItems: "center", justifyContent: "center",
                            fontSize: "0.72rem",
                            color: "var(--gold-primary)",
                            fontWeight: 700,
                            flexShrink: 0,
                          }}>
                            {s.n}
                          </div>
                          <div>
                            <span style={{ fontSize: "0.82rem", color: "var(--text-primary)", fontWeight: 600 }}>
                              {s.label}
                            </span>
                            <span style={{ fontSize: "0.78rem", color: "var(--text-muted)", marginLeft: 8 }}>
                              {s.desc}
                            </span>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Tech Stack Card */}
                <div className="glass-card" style={{ padding: "24px 28px" }}>
                  <h3 style={{
                    fontFamily: "'Cinzel', serif",
                    fontSize: "0.75rem",
                    letterSpacing: "0.15em",
                    color: "var(--text-muted)",
                    textTransform: "uppercase",
                    marginBottom: 16,
                  }}>
                    Technology Stack
                  </h3>
                  <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
                    {[
                      { icon: "🤖", tech: "Gemini 1.5 Flash",   cost: "Free API"  },
                      { icon: "🎙️", tech: "Kokoro-82M",         cost: "Offline"   },
                      { icon: "🔬", tech: "WhisperX",           cost: "Open"      },
                      { icon: "🎬", tech: "MoviePy + FFmpeg",   cost: "Free"      },
                      { icon: "💬", tech: "pysubs2 ASS",        cost: "Open"      },
                      { icon: "🔍", tech: "FAISS + ST",         cost: "Free"      },
                    ].map(t => (
                      <div key={t.tech} style={{
                        padding: "10px 12px",
                        background: "var(--bg-elevated)",
                        borderRadius: "var(--radius-sm)",
                        border: "1px solid var(--border-subtle)",
                      }}>
                        <div style={{ fontSize: "0.85rem" }}>{t.icon} <span style={{ color: "var(--text-primary)", fontWeight: 500 }}>{t.tech}</span></div>
                        <div style={{ fontSize: "0.72rem", color: "var(--green-ok)", marginTop: 3 }}>{t.cost}</div>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Cost counter */}
                <div style={{
                  padding: "16px 24px",
                  border: "1px solid var(--border-gold)",
                  borderRadius: "var(--radius-md)",
                  background: "var(--gold-glow)",
                  textAlign: "center",
                }}>
                  <div style={{ fontSize: "2rem", fontWeight: 900, color: "var(--gold-primary)", fontFamily: "'Cinzel', serif" }}>
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

        {/* ── Footer ── */}
        <footer style={{
          borderTop: "1px solid var(--border-subtle)",
          padding: "28px 0",
          textAlign: "center",
        }}>
          <div className="container">
            <p style={{ fontSize: "0.8rem", color: "var(--text-muted)" }}>
              THE INNER CITADEL — Autonomous Stoic Video Pipeline ·{" "}
              <span style={{ color: "var(--gold-dim)" }}>100% Open Source</span>
              {" · "}
              <a href="https://github.com" target="_blank" rel="noopener noreferrer"
                style={{ color: "var(--text-muted)", textDecoration: "none" }}>
                GitHub
              </a>
            </p>
          </div>
        </footer>
      </main>

      {/* ── Responsive styles ── */}
      <style>{`
        @media (max-width: 768px) {
          section > div.container > div {
            grid-template-columns: 1fr !important;
          }
        }
      `}</style>
    </>
  );
}
