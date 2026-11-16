// Dates and times as a person reads them. The server sends UTC ISO strings. Everything here shows
// the viewer's local time, with the date first so a list sorts by eye.

const DATE = new Intl.DateTimeFormat("en-GB", { day: "numeric", month: "short", year: "numeric" });
const TIME = new Intl.DateTimeFormat("en-GB", { hour: "2-digit", minute: "2-digit" });
const TIME_SECONDS = new Intl.DateTimeFormat("en-GB", { hour: "2-digit", minute: "2-digit", second: "2-digit" });

/** "3 Oct 2026, 16:42" */
export function formatWhen(iso: string): string {
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return iso;
  return `${DATE.format(date)}, ${TIME.format(date)}`;
}

/** "16:42:07", for an audit row where seconds matter */
export function formatClock(iso: string): string {
  const date = new Date(iso);
  return Number.isNaN(date.getTime()) ? iso : TIME_SECONDS.format(date);
}

/** "3 Oct 2026" from a date-only or full ISO string */
export function formatDay(iso: string): string {
  const date = new Date(iso.length === 10 ? `${iso}T00:00:00` : iso);
  return Number.isNaN(date.getTime()) ? iso : DATE.format(date);
}

/** "5 minutes ago". Coarse on purpose: a queue shows age, not a timestamp. */
export function formatAge(iso: string, nowMs: number = Date.now()): string {
  const minutes = Math.max(0, Math.round((nowMs - new Date(iso).getTime()) / 60_000));
  if (Number.isNaN(minutes)) return iso;
  if (minutes < 1) return "just now";
  if (minutes < 60) return `${minutes} min ago`;
  const hours = Math.round(minutes / 60);
  if (hours < 24) return `${hours} h ago`;
  const days = Math.round(hours / 24);
  return `${days} day${days === 1 ? "" : "s"} ago`;
}
