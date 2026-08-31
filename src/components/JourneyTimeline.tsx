"use client";

import { useEffect, useState } from "react";
import { Badge } from "@/components/ui/badge";
import type { JourneyEvent } from "@/data/types";

const TYPE_LABELS: Record<JourneyEvent["type"], string> = {
  enrollment: "Enrollment",
  sale: "Sale",
  loan: "Loan",
  repayment: "Repayment",
  tree: "Trees",
  buyback: "Buyback",
};

export function JourneyTimeline({ glClientId }: { glClientId: string }) {
  const [events, setEvents] = useState<JourneyEvent[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    fetch(`/api/farmers/${glClientId}/journey`)
      .then(async (response) => {
        if (!response.ok) throw new Error(`Request failed (${response.status})`);
        return (await response.json()) as JourneyEvent[];
      })
      .then((data) => {
        if (!cancelled) setEvents(data);
      })
      .catch(() => {
        if (!cancelled) setError("Could not load this farmer's journey.");
      });

    return () => {
      cancelled = true;
    };
  }, [glClientId]);

  if (error) return <p className="text-sm text-destructive">{error}</p>;
  if (!events) return <p className="text-sm text-muted-foreground">Loading timeline…</p>;
  if (events.length === 0) {
    return <p className="text-sm text-muted-foreground">No activity recorded yet.</p>;
  }

  return (
    <ol className="flex flex-col gap-4 border-l pl-6">
      {events.map((event) => (
        <li key={event.id} className="relative">
          <span className="absolute -left-[29px] top-1.5 h-2.5 w-2.5 rounded-full bg-primary" />
          <div className="flex items-center gap-2">
            <Badge variant="outline">{TYPE_LABELS[event.type]}</Badge>
            <span className="text-sm text-muted-foreground">{event.date}</span>
          </div>
          <p className="mt-1 text-sm">{event.description}</p>
          {event.amount != null && (
            <p className="text-sm text-muted-foreground">
              {event.amount.toLocaleString()} {event.currency}
            </p>
          )}
        </li>
      ))}
    </ol>
  );
}
