"use client";

import { ArrowRight } from "lucide-react";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { useCreateRun } from "@/lib/api/queries";

// One vague, one half specified, one complete, so the three paths through the clarifier are easy to show
const EXAMPLES = [
  "Prepare the leadership brief",
  "Where did we miss target this year, and what should we do about it?",
  "Placement and research brief for the Governing Council for 2025-26",
];

export function NewRunForm() {
  const router = useRouter();
  const create = useCreateRun();
  const [text, setText] = useState("");
  const ready = text.trim().length >= 3;

  return (
    <form
      className="flex flex-col gap-4"
      onSubmit={(event) => {
        event.preventDefault();
        if (!ready || create.isPending) return;
        create.mutate(text, { onSuccess: (run) => router.push(`/runs/${run.id}`) });
      }}
    >
      <div className="flex flex-col gap-2">
        <Label htmlFor="request" className="text-base font-medium">
          What do you need a brief on?
        </Label>
        <Textarea
          id="request"
          value={text}
          onChange={(event) => setText(event.target.value)}
          rows={4}
          maxLength={1000}
          placeholder="For example: where are we off target, and what are our options?"
          aria-describedby="request-help"
          className="min-h-28 text-base"
        />
        <p id="request-help" className="text-sm text-muted-foreground">
          Plain words are enough. The agent asks about anything it needs, and you review its plan before anything runs.
        </p>
      </div>

      <div className="flex flex-col gap-2">
        <p className="text-sm font-medium text-muted-foreground">Or start from an example</p>
        <ul className="flex flex-wrap gap-2">
          {EXAMPLES.map((example) => (
            <li key={example}>
              <Button type="button" variant="outline" size="sm" onClick={() => setText(example)}>
                {example}
              </Button>
            </li>
          ))}
        </ul>
      </div>

      {create.isError && (
        <Alert variant="destructive">
          <AlertDescription className="text-base">{create.error.message}</AlertDescription>
        </Alert>
      )}

      <div>
        <Button type="submit" size="lg" disabled={!ready || create.isPending}>
          {create.isPending ? "Starting" : "Start"}
          <ArrowRight aria-hidden data-icon="inline-end" />
        </Button>
      </div>
    </form>
  );
}
