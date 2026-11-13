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

export function looksLikeYouTubeUrl(raw: string): boolean {
  const text = raw.trim();
  if (!text) return false;
  try {
    const url = new URL(text.includes("://") ? text : `https://${text}`);
    return url.protocol === "https:" && HOSTS.has(url.hostname.toLowerCase());
  } catch {
    return false;
  }
}
