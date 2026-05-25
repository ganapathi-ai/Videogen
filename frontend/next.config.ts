/** @type {import('next').NextConfig} */
const nextConfig = {
  // Allow images from any source (for thumbnails)
  images: {
    remotePatterns: [
      { protocol: "https", hostname: "**" },
      { protocol: "http",  hostname: "localhost" },
    ],
  },

  // Proxy /api/* and /exports/* to local or Ngrok backend
  // This only applies in local dev. On Vercel, the frontend
  // calls NEXT_PUBLIC_BACKEND_URL directly (already set to Ngrok URL).
  async rewrites() {
    const backendUrl =
      process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8000";
    return [
      { source: "/api/:path*",     destination: `${backendUrl}/api/:path*` },
      { source: "/exports/:path*", destination: `${backendUrl}/exports/:path*` },
    ];
  },

  // Headers for SSE (Server-Sent Events)
  async headers() {
    return [
      {
        source: "/api/stream-progress/:jobId",
        headers: [
          { key: "Cache-Control",     value: "no-cache, no-transform" },
          { key: "X-Accel-Buffering", value: "no" },
          { key: "Content-Type",      value: "text/event-stream" },
        ],
      },
    ];
  },
};

export default nextConfig;
