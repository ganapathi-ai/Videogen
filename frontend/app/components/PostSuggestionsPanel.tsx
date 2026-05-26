"use client";

import { useState, useEffect, useCallback } from "react";

// ─────────────────────────────────────────────────────────────────────────────
// PostSuggestionsPanel
// Auto-generates SEO-optimised post copy after every video generation.
// Features:
//  • YouTube titles (3 variants) + full description
//  • Instagram caption with emojis + hashtags
//  • Twitter/X 3-tweet thread
//  • 30 SEO hashtag bank (click to copy)
//  • Thumbnail prompt (always shown) — paste into Midjourney/DALL-E
//  • One-click copy for every field
// ─────────────────────────────────────────────────────────────────────────────

interface Props {
  backendUrl: string;
  title: string;
  topic: string;
  channel: string;
  duration: number;    // seconds
  scriptExcerpt: string;
  accentColor: string;
}

interface SuggestionsData {
  youtube_titles:      string[];
  youtube_description: string;
  instagram_caption:   string;
  twitter_thread:      string[];
  hashtags:            string[];
  thumbnail_prompt:    string;
}

// ── Minimal copy-to-clipboard button ────────────────────────────────────────
function CopyBtn({ text, accent }: { text: string; accent: string }) {
  const [copied, setCopied] = useState(false);
  const copy = () => {
    navigator.clipboard.writeText(text).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 1800);
    });
  };
  return (
    <button onClick={copy} style={{
      background: copied ? "rgba(34,197,94,0.18)" : "rgba(255,255,255,0.07)",
      border: `1px solid ${copied ? "rgba(34,197,94,0.4)" : "rgba(255,255,255,0.12)"}`,
      borderRadius: 8, padding: "5px 14px",
      fontSize: "0.72rem", letterSpacing: "0.06em",
      color: copied ? "#4ade80" : "var(--text-muted)",
      cursor: "pointer", transition: "all 0.25s ease",
      fontFamily: "inherit", whiteSpace: "nowrap",
    }}>
      {copied ? "✓ Copied" : "Copy"}
    </button>
  );
}

// ── Single section card ───────────────────────────────────────────────────────
function Section({
  icon, label, children, accent,
}: { icon: string; label: string; children: React.ReactNode; accent: string }) {
  return (
    <div style={{
      background: "rgba(255,255,255,0.03)",
      border: "1px solid rgba(255,255,255,0.08)",
      borderRadius: 14, padding: "18px 20px", marginBottom: 14,
    }}>
      <div style={{
        display: "flex", alignItems: "center", gap: 8,
        marginBottom: 12,
        fontSize: "0.78rem", fontWeight: 700,
        letterSpacing: "0.08em", textTransform: "uppercase",
        color: accent,
      }}>
        <span style={{ fontSize: "1rem" }}>{icon}</span>
        {label}
      </div>
      {children}
    </div>
  );
}

// ── Text field with copy ─────────────────────────────────────────────────────
function TextField({
  value, accent, rows = 3,
}: { value: string; accent: string; rows?: number }) {
  return (
    <div style={{ position: "relative" }}>
      <textarea
        readOnly value={value}
        rows={rows}
        style={{
          width: "100%", background: "rgba(0,0,0,0.3)",
          border: "1px solid rgba(255,255,255,0.1)",
          borderRadius: 10, padding: "10px 14px",
          color: "var(--text-primary)", fontSize: "0.82rem",
          lineHeight: 1.6, resize: "vertical",
          fontFamily: "inherit", boxSizing: "border-box",
        }}
      />
      <div style={{ position: "absolute", top: 8, right: 8 }}>
        <CopyBtn text={value} accent={accent} />
      </div>
    </div>
  );
}

// ── Hashtag chip cloud ────────────────────────────────────────────────────────
function HashtagCloud({
  tags, accent,
}: { tags: string[]; accent: string }) {
  const [copiedAll, setCopiedAll] = useState(false);
  const copyAll = () => {
    navigator.clipboard.writeText(tags.map(t => `#${t}`).join(" ")).then(() => {
      setCopiedAll(true);
      setTimeout(() => setCopiedAll(false), 1800);
    });
  };
  return (
    <div>
      <div style={{ display: "flex", flexWrap: "wrap", gap: 6, marginBottom: 10 }}>
        {tags.map((tag, i) => (
          <span
            key={i}
            onClick={() => navigator.clipboard.writeText(`#${tag}`)}
            title="Click to copy"
            style={{
              background: `${accent}18`,
              border: `1px solid ${accent}40`,
              borderRadius: 20, padding: "3px 10px",
              fontSize: "0.73rem", color: accent,
              cursor: "pointer", transition: "background 0.2s",
              userSelect: "none",
            }}
            onMouseOver={e => (e.currentTarget.style.background = `${accent}30`)}
            onMouseOut={e  => (e.currentTarget.style.background = `${accent}18`)}
          >
            #{tag}
          </span>
        ))}
      </div>
      <button onClick={copyAll} style={{
        background: copiedAll ? "rgba(34,197,94,0.15)" : `${accent}15`,
        border: `1px solid ${copiedAll ? "rgba(34,197,94,0.4)" : `${accent}40`}`,
        borderRadius: 8, padding: "6px 18px",
        fontSize: "0.73rem", color: copiedAll ? "#4ade80" : accent,
        cursor: "pointer", letterSpacing: "0.06em",
        fontFamily: "inherit", transition: "all 0.25s",
      }}>
        {copiedAll ? "✓ All Copied!" : "Copy All 30 Hashtags"}
      </button>
    </div>
  );
}

// ── Thumbnail Prompt Box (highlighted, always visible) ───────────────────────
function ThumbnailPrompt({ prompt, accent }: { prompt: string; accent: string }) {
  const [expanded, setExpanded] = useState(true);
  return (
    <div style={{
      background: `linear-gradient(135deg, ${accent}12 0%, rgba(0,0,0,0.4) 100%)`,
      border: `1px solid ${accent}50`,
      borderRadius: 14, padding: "18px 20px", marginBottom: 14,
      position: "relative", overflow: "hidden",
    }}>
      {/* Glow strip */}
      <div style={{
        position: "absolute", top: 0, left: 0, right: 0, height: 2,
        background: `linear-gradient(90deg, transparent, ${accent}, transparent)`,
      }} />
      <div style={{
        display: "flex", justifyContent: "space-between",
        alignItems: "center", marginBottom: expanded ? 12 : 0,
      }}>
        <div style={{
          display: "flex", alignItems: "center", gap: 8,
          fontSize: "0.78rem", fontWeight: 700,
          letterSpacing: "0.08em", textTransform: "uppercase",
          color: accent,
        }}>
          <span style={{ fontSize: "1rem" }}>🖼️</span>
          Thumbnail Prompt
          <span style={{
            background: `${accent}25`, border: `1px solid ${accent}50`,
            borderRadius: 20, padding: "1px 8px",
            fontSize: "0.65rem", color: accent, fontWeight: 600,
          }}>Midjourney / DALL·E 3</span>
        </div>
        <div style={{ display: "flex", gap: 8 }}>
          <CopyBtn text={prompt} accent={accent} />
          <button onClick={() => setExpanded(!expanded)} style={{
            background: "rgba(255,255,255,0.07)",
            border: "1px solid rgba(255,255,255,0.12)",
            borderRadius: 8, padding: "5px 10px",
            fontSize: "0.72rem", color: "var(--text-muted)",
            cursor: "pointer", fontFamily: "inherit",
          }}>
            {expanded ? "▲" : "▼"}
          </button>
        </div>
      </div>
      {expanded && (
        <p style={{
          fontSize: "0.82rem", color: "var(--text-secondary)",
          lineHeight: 1.7, margin: 0,
          background: "rgba(0,0,0,0.25)",
          borderRadius: 8, padding: "10px 14px",
          border: "1px solid rgba(255,255,255,0.06)",
        }}>
          {prompt}
        </p>
      )}
    </div>
  );
}

// ── Tab selector ──────────────────────────────────────────────────────────────
function TabBar({
  tabs, active, onChange, accent,
}: { tabs: string[]; active: string; onChange: (t: string) => void; accent: string }) {
  return (
    <div style={{
      display: "flex", gap: 4, marginBottom: 16,
      background: "rgba(0,0,0,0.3)", borderRadius: 10,
      padding: 4,
    }}>
      {tabs.map(t => (
        <button key={t} onClick={() => onChange(t)} style={{
          flex: 1,
          background: active === t ? `${accent}22` : "transparent",
          border: active === t ? `1px solid ${accent}50` : "1px solid transparent",
          borderRadius: 7, padding: "6px 10px",
          fontSize: "0.73rem", fontWeight: active === t ? 700 : 400,
          color: active === t ? accent : "var(--text-muted)",
          cursor: "pointer", transition: "all 0.2s",
          fontFamily: "inherit", letterSpacing: "0.03em",
        }}>
          {t}
        </button>
      ))}
    </div>
  );
}

// ── Main Component ────────────────────────────────────────────────────────────
export default function PostSuggestionsPanel({
  backendUrl, title, topic, channel, duration, scriptExcerpt, accentColor,
}: Props) {
  const [data,    setData]    = useState<SuggestionsData | null>(null);
  const [loading, setLoading] = useState(false);
  const [error,   setError]   = useState<string | null>(null);
  const [tab,     setTab]     = useState("YouTube");
  const [open,    setOpen]    = useState(true);

  const accent = accentColor || "#C4A064";

  const fetchSuggestions = useCallback(async () => {
    setLoading(true); setError(null);
    try {
      const resp = await fetch(`${backendUrl}/api/post-suggestions`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ title, topic, channel, duration, script_excerpt: scriptExcerpt }),
      });
      const json = await resp.json();
      if (json.success && json.data) {
        setData(json.data);
      } else {
        setData(json.data || null);
        setError(json.error || "Could not generate suggestions");
      }
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Network error");
    } finally {
      setLoading(false);
    }
  }, [backendUrl, title, topic, channel, duration, scriptExcerpt]);

  // Auto-fetch on mount
  useEffect(() => { fetchSuggestions(); }, [fetchSuggestions]);

  return (
    <div className="glass-card" style={{
      marginTop: 20,
      background: "rgba(15,15,25,0.85)",
      border: `1px solid ${accent}30`,
      borderRadius: 20, overflow: "hidden",
    }}>
      {/* Header */}
      <div
        onClick={() => setOpen(!open)}
        style={{
          padding: "18px 24px",
          display: "flex", justifyContent: "space-between", alignItems: "center",
          cursor: "pointer",
          background: `linear-gradient(135deg, ${accent}10 0%, transparent 100%)`,
          borderBottom: open ? `1px solid ${accent}25` : "none",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <div style={{
            width: 36, height: 36, borderRadius: 10,
            background: `${accent}20`, border: `1px solid ${accent}40`,
            display: "flex", alignItems: "center", justifyContent: "center",
            fontSize: "1.1rem",
          }}>📢</div>
          <div>
            <div style={{
              fontSize: "0.9rem", fontWeight: 700,
              color: "var(--text-primary)",
              fontFamily: "'Cinzel', serif", letterSpacing: "0.04em",
            }}>
              Post Suggestions
            </div>
            <div style={{ fontSize: "0.72rem", color: "var(--text-muted)", marginTop: 2 }}>
              SEO-optimised captions · hashtags · thumbnail prompt
              {duration >= 120 && (
                <span style={{
                  marginLeft: 8, background: `${accent}20`,
                  border: `1px solid ${accent}40`,
                  borderRadius: 10, padding: "1px 7px",
                  fontSize: "0.65rem", color: accent,
                }}>Long Video</span>
              )}
            </div>
          </div>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          {!loading && (
            <button
              onClick={e => { e.stopPropagation(); fetchSuggestions(); }}
              style={{
                background: `${accent}18`, border: `1px solid ${accent}40`,
                borderRadius: 8, padding: "5px 14px",
                fontSize: "0.72rem", color: accent,
                cursor: "pointer", fontFamily: "inherit",
                letterSpacing: "0.05em",
              }}
            >↺ Refresh</button>
          )}
          <span style={{ color: "var(--text-muted)", fontSize: "0.8rem" }}>
            {open ? "▲" : "▼"}
          </span>
        </div>
      </div>

      {/* Body */}
      {open && (
        <div style={{ padding: "22px 24px" }}>

          {/* Loading state */}
          {loading && (
            <div style={{
              display: "flex", flexDirection: "column",
              alignItems: "center", padding: "32px 0", gap: 16,
            }}>
              <div style={{
                width: 44, height: 44, borderRadius: "50%",
                border: `3px solid ${accent}30`,
                borderTop: `3px solid ${accent}`,
                animation: "spin 0.9s linear infinite",
              }} />
              <p style={{ color: "var(--text-muted)", fontSize: "0.82rem" }}>
                Generating SEO-optimised post copy…
              </p>
              <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
            </div>
          )}

          {/* Error state */}
          {error && !loading && (
            <div style={{
              background: "rgba(239,68,68,0.08)",
              border: "1px solid rgba(239,68,68,0.25)",
              borderRadius: 10, padding: "12px 16px",
              color: "#f87171", fontSize: "0.82rem", marginBottom: 14,
            }}>
              ⚠️ {error} — suggestions may be limited
            </div>
          )}

          {/* Main content */}
          {data && !loading && (
            <>
              {/* Thumbnail prompt — always at top */}
              <ThumbnailPrompt prompt={data.thumbnail_prompt} accent={accent} />

              {/* Platform tabs */}
              <TabBar
                tabs={["YouTube", "Instagram", "Twitter / X", "Hashtags"]}
                active={tab} onChange={setTab} accent={accent}
              />

              {/* YouTube tab */}
              {tab === "YouTube" && (
                <div>
                  <Section icon="🎬" label="Title Variants (A/B Test)" accent={accent}>
                    <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                      {(data.youtube_titles || []).map((t, i) => (
                        <div key={i} style={{
                          display: "flex", alignItems: "center",
                          gap: 10,
                          background: "rgba(0,0,0,0.25)",
                          borderRadius: 8, padding: "8px 12px",
                          border: "1px solid rgba(255,255,255,0.07)",
                        }}>
                          <span style={{
                            width: 20, height: 20, borderRadius: "50%",
                            background: `${accent}20`, border: `1px solid ${accent}40`,
                            display: "flex", alignItems: "center", justifyContent: "center",
                            fontSize: "0.65rem", fontWeight: 700, color: accent,
                            flexShrink: 0,
                          }}>{i + 1}</span>
                          <span style={{
                            flex: 1, fontSize: "0.82rem",
                            color: "var(--text-primary)",
                          }}>{t}</span>
                          <CopyBtn text={t} accent={accent} />
                        </div>
                      ))}
                    </div>
                  </Section>
                  <Section icon="📝" label="YouTube Description" accent={accent}>
                    <TextField value={data.youtube_description} accent={accent} rows={6} />
                    <p style={{
                      fontSize: "0.7rem", color: "var(--text-muted)",
                      marginTop: 6, marginBottom: 0,
                    }}>
                      ✓ SEO keywords embedded · ✓ CTA included · {duration >= 120 ? "✓ Timestamps added" : "✓ Short-video optimised"}
                    </p>
                  </Section>
                </div>
              )}

              {/* Instagram tab */}
              {tab === "Instagram" && (
                <Section icon="📸" label="Instagram / Reels Caption" accent={accent}>
                  <TextField value={data.instagram_caption} accent={accent} rows={7} />
                  <p style={{
                    fontSize: "0.7rem", color: "var(--text-muted)",
                    marginTop: 6, marginBottom: 0,
                  }}>
                    ✓ Hook → Value → CTA format · ✓ Reels-optimised · ✓ Inline hashtags
                  </p>
                </Section>
              )}

              {/* Twitter / X tab */}
              {tab === "Twitter / X" && (
                <Section icon="🐦" label="Twitter / X Thread" accent={accent}>
                  <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
                    {(data.twitter_thread || []).map((tweet, i) => (
                      <div key={i} style={{
                        background: "rgba(0,0,0,0.3)",
                        border: "1px solid rgba(255,255,255,0.08)",
                        borderRadius: 10, padding: "12px 14px",
                      }}>
                        <div style={{
                          display: "flex", justifyContent: "space-between",
                          alignItems: "flex-start", gap: 10,
                        }}>
                          <div style={{ flex: 1 }}>
                            <span style={{
                              fontSize: "0.65rem", fontWeight: 700,
                              color: accent, letterSpacing: "0.06em",
                              textTransform: "uppercase",
                            }}>
                              {i === 0 ? "🧵 Thread 1/3" : i === 1 ? "🧵 Thread 2/3" : "🧵 Thread 3/3 — CTA"}
                            </span>
                            <p style={{
                              fontSize: "0.83rem", color: "var(--text-primary)",
                              lineHeight: 1.6, margin: "6px 0 0 0",
                            }}>{tweet}</p>
                            <p style={{
                              fontSize: "0.68rem", color: "var(--text-muted)",
                              margin: "4px 0 0 0",
                            }}>
                              {tweet.length}/280 chars
                              {tweet.length > 280 && (
                                <span style={{ color: "#f87171" }}> ⚠️ Over limit</span>
                              )}
                            </p>
                          </div>
                          <CopyBtn text={tweet} accent={accent} />
                        </div>
                      </div>
                    ))}
                    <CopyBtn
                      text={(data.twitter_thread || []).join("\n\n")}
                      accent={accent}
                    />
                  </div>
                </Section>
              )}

              {/* Hashtags tab */}
              {tab === "Hashtags" && (
                <Section icon="#️⃣" label="SEO Hashtag Bank (click any to copy)" accent={accent}>
                  <HashtagCloud tags={data.hashtags || []} accent={accent} />
                  <p style={{
                    fontSize: "0.7rem", color: "var(--text-muted)",
                    marginTop: 10, marginBottom: 0,
                  }}>
                    ✓ 10 broad · ✓ 10 medium · ✓ 10 niche/channel-specific
                  </p>
                </Section>
              )}
            </>
          )}
        </div>
      )}
    </div>
  );
}
