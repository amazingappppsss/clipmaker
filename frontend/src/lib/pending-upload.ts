/**
 * Holds a file the visitor dropped on the landing page while they sign in.
 *
 * Memory-only on purpose: a File cannot be serialised to storage, and keeping private videos
 * out of browser storage is safer. It survives client-side navigation (dev login, already
 * signed in) but not a full page reload (magic-link redirect) — then the user re-selects.
 */
let pending: File | null = null;

export function setPendingUpload(file: File | null): void {
  pending = file;
}

/** True if a file is waiting (without consuming it). */
export function hasPendingUpload(): boolean {
  return pending !== null;
}

/** Returns the pending file once and clears it. */
export function takePendingUpload(): File | null {
  const file = pending;
  pending = null;
  return file;
}

const LINK_KEY = "clipmaker.pendingLink";

/**
 * A link pasted on the landing page before signing in. Unlike a File, a link is plain text,
 * so it is kept in localStorage and survives the magic-link email redirect.
 */
export function setPendingLink(url: string): void {
  try {
    window.localStorage.setItem(LINK_KEY, url);
  } catch {
    /* storage unavailable: the user re-pastes the link */
  }
}

/** Returns the pending link once and clears it. */
export function takePendingLink(): string | null {
  try {
    const url = window.localStorage.getItem(LINK_KEY);
    window.localStorage.removeItem(LINK_KEY);
    return url;
  } catch {
    return null;
  }
}
