"use client";

import { useQueryClient } from "@tanstack/react-query";
import { useEffect, useRef, useState } from "react";

import { keys } from "@/lib/api/queries";
import type { RunEvent } from "@/lib/api/types";

export type Connection = "connecting" | "live" | "reconnecting" | "ended";

/**
 * A run's progress as it happens, read from the server's event stream. The browser reconnects by
 * itself and the server resumes from the last event it was sent, so a dropped connection loses
 * nothing. The stream says when it is over, and the run record is refreshed at that moment so the
 * page moves on to the next stage.
 *
 * `statusKey` is the run's status. When it changes (a stopped run is resumed, a person decides),
 * the stream is opened again from the last event seen.
 */
export function useRunEvents(runId: string, enabled: boolean, statusKey: string) {
  const client = useQueryClient();
  const [events, setEvents] = useState<RunEvent[]>([]);
  const [connection, setConnection] = useState<Connection>("connecting");
  const lastId = useRef(0);

  useEffect(() => {
    if (!enabled) return;
    const source = new EventSource(`/api/runs/${encodeURIComponent(runId)}/events?after=${lastId.current}`);

    source.onopen = () => setConnection("live");
    source.onerror = () => {
      // EventSource retries on its own. CLOSED means the server refused, which retrying cannot fix
      setConnection(source.readyState === EventSource.CLOSED ? "ended" : "reconnecting");
    };
    source.addEventListener("node", (message) => {
      const event = JSON.parse((message as MessageEvent<string>).data) as RunEvent;
      if (event.id <= lastId.current) return; // a reconnect can repeat the last event
      lastId.current = event.id;
      setEvents((previous) => [...previous, event]);
    });
    source.addEventListener("end", () => {
      source.close();
      setConnection("ended");
      void client.invalidateQueries({ queryKey: keys.run(runId) });
    });

    return () => source.close();
  }, [runId, enabled, statusKey, client]);

  return { events, connection };
}

/** The current time, ticking while `active`, so a step that is still running shows its bar growing. */
export function useNow(active: boolean, everyMs = 250): number {
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    if (!active) return;
    const timer = setInterval(() => setNow(Date.now()), everyMs);
    return () => clearInterval(timer);
  }, [active, everyMs]);
  return now;
}
