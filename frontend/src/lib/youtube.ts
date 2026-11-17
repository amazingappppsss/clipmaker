/**
 * Light client-side check so obvious typos fail instantly. The backend's allow-list
 * (media/url_import.py) is the real gate.
 */
const HOSTS = new Set([
  "youtube.com",
  "www.youtube.com",
  "m.youtube.com",
  "music.youtube.com",
  "youtu.be",
]);

/** Twitch VODs and clips, where stream clippers actually work. */
const TWITCH_HOSTS = new Set([
  "twitch.tv",
  "www.twitch.tv",
  "m.twitch.tv",
  "clips.twitch.tv",
]);

function host(raw: string): string | null {
  const text = raw.trim();
  if (!text) return null;
  try {
    const url = new URL(text.includes("://") ? text : `https://${text}`);
    return url.protocol === "https:" ? url.hostname.toLowerCase() : null;
  } catch {
    return null;
  }
}

export function looksLikeYouTubeUrl(raw: string): boolean {
  const name = host(raw);
  return name !== null && HOSTS.has(name);
}

/**
 * Any link the backend will accept. Kept in step with ALLOWED_HOSTS in media/url_import.py —
 * a stricter check here would reject Twitch links the API is happy to take.
 */
export function looksLikeSourceUrl(raw: string): boolean {
  const name = host(raw);
  return name !== null && (HOSTS.has(name) || TWITCH_HOSTS.has(name));
}

/** Public thumbnail for a YouTube link (shown while the video is being fetched), or null. */
export function youtubeThumbnail(raw: string | null | undefined): string | null {
  if (!raw || !looksLikeYouTubeUrl(raw)) return null;
  const url = new URL(raw.includes("://") ? raw.trim() : `https://${raw.trim()}`);
  const host = url.hostname.toLowerCase();
  let id: string | null = null;
  if (host === "youtu.be") id = url.pathname.split("/")[1] ?? null;
  else if (url.pathname === "/watch") id = url.searchParams.get("v");
  else {
    const m = url.pathname.match(/^\/(?:shorts|live|embed)\/([^/?#]+)/);
    id = m?.[1] ?? null;
  }
  return id && /^[\w-]{11}$/.test(id) ? `https://i.ytimg.com/vi/${id}/hqdefault.jpg` : null;
}
