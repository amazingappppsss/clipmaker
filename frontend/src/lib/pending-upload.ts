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

/** Returns the pending file once and clears it. */
export function takePendingUpload(): File | null {
  const file = pending;
  pending = null;
  return file;
}
