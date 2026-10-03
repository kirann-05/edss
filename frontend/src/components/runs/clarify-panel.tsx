"use client";

import { cn } from "cn";
import { Bot, Check, UserRound } from "lucide-react";
import { useState } from "react";

import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useAnswerRun, useSkipQuestions } from "@/lib/api/queries";
import type { Question, Run } from "@/lib/api/types";

/** One turn of the conversation. The person's turns sit on the right, the agent's on the left. */
export function Turn({
  from,
  children,
  className,
}: {
  from: "person" | "agent";
  children: React.ReactNode;
  className?: string;
}) {
  const person = from === "person";
  const Icon = person ? UserRound : Bot;
  return (
    <div className={cn("flex items-start gap-3", person && "flex-row-reverse")}>
      <span
        aria-hidden
        className={cn(
          "mt-1 grid size-8 shrink-0 place-items-center rounded-full border",
          person ? "border-primary/30 bg-primary/10 text-primary" : "bg-card text-muted-foreground",
        )}
      >
        <Icon className="size-4" />
      </span>
      <div
        className={cn(
          "flex max-w-[44rem] min-w-0 flex-col gap-2 rounded-2xl px-4 py-3 text-base",
          person ? "rounded-tr-md bg-primary/10" : "rounded-tl-md border bg-card",
          className,
        )}
      >
        <span className="sr-only">{person ? "You said:" : "The planner said:"}</span>
        {children}
      </div>
    </div>
  );
}

/** The request and every answer so far, so a reload shows the whole conversation. */
export function Conversation({ run }: { run: Run }) {
  return (
    <div className="flex flex-col gap-4">
      <Turn from="person">
        <p>{run.request}</p>
      </Turn>
      {run.answers.map((answer) => (
        <div key={answer.question_id} className="flex flex-col gap-4">
          <Turn from="agent">
            <p>{answer.question}</p>
          </Turn>
          <Turn from="person">
            <p>{answer.answer}</p>
          </Turn>
        </div>
      ))}
    </div>
  );
}

function QuestionField({
  question,
  value,
  onChange,
}: {
  question: Question;
  value: string;
  onChange: (value: string) => void;
}) {
  const typed = value !== "" && !question.choices.includes(value) ? value : "";
  return (
    <fieldset className="flex flex-col gap-3 rounded-xl border bg-background p-4">
      <legend className="sr-only">{question.text}</legend>
      <div className="flex flex-col gap-1">
        <p aria-hidden className="text-base font-semibold">
          {question.text}
        </p>
        <p className="text-sm text-muted-foreground">Why I ask: {question.why}</p>
      </div>
      {question.choices.length > 0 && (
        <div className="flex flex-wrap gap-2">
          {question.choices.map((choice) => {
            const checked = value === choice;
            return (
              <label
                key={choice}
                className={cn(
                  "flex min-h-11 cursor-pointer items-center gap-2 rounded-lg border px-3 text-base transition-colors",
                  "has-[:focus-visible]:ring-3 has-[:focus-visible]:ring-ring/50",
                  checked ? "border-primary bg-primary/10 font-medium" : "bg-card hover:bg-muted",
                )}
              >
                <input
                  type="radio"
                  name={question.id}
                  value={choice}
                  checked={checked}
                  onChange={() => onChange(choice)}
                  className="sr-only"
                />
                {checked && <Check aria-hidden className="size-4 text-primary" />}
                {choice}
              </label>
            );
          })}
        </div>
      )}
      <Input
        value={typed}
        onChange={(event) => onChange(event.target.value)}
        aria-label={`Your own answer to: ${question.text}`}
        placeholder={question.choices.length > 0 ? "Or write your own answer" : "Your answer"}
        className="h-11 text-base"
      />
    </fieldset>
  );
}

export function ClarifyPanel({ run }: { run: Run }) {
  const answer = useAnswerRun(run.id);
  const skip = useSkipQuestions(run.id);
  const [values, setValues] = useState<Record<string, string>>({});

  const answered = run.questions
    .map((q) => ({ question_id: q.id, answer: (values[q.id] ?? "").trim() }))
    .filter((a) => a.answer !== "");
  const busy = answer.isPending || skip.isPending;
  const error = answer.error ?? skip.error;

  return (
    <section aria-labelledby="clarify-heading" className="flex flex-col gap-4">
      <h2 id="clarify-heading" className="sr-only">
        Questions from the planner
      </h2>
      <Conversation run={run} />
      <Turn from="agent" className="w-full max-w-[44rem]">
        <p>
          {run.answers.length === 0
            ? "Before I plan this, I need to know a few things."
            : "Thanks. A little more and I can propose a plan."}
        </p>
        <form
          className="flex flex-col gap-3"
          onSubmit={(event) => {
            event.preventDefault();
            if (answered.length === 0 || busy) return;
            answer.mutate(answered, { onSuccess: () => setValues({}) });
          }}
        >
          {run.questions.map((question) => (
            <QuestionField
              key={question.id}
              question={question}
              value={values[question.id] ?? ""}
              onChange={(value) => setValues((previous) => ({ ...previous, [question.id]: value }))}
            />
          ))}
          {error && (
            <Alert variant="destructive">
              <AlertDescription className="text-base">{error.message}</AlertDescription>
            </Alert>
          )}
          <div className="flex flex-wrap items-center gap-3">
            <Button type="submit" disabled={answered.length === 0 || busy}>
              {answer.isPending ? "Sending" : "Continue"}
            </Button>
            <Button type="button" variant="outline" disabled={busy} onClick={() => skip.mutate()}>
              {skip.isPending ? "Planning" : "Skip, use sensible defaults"}
            </Button>
            <span className="text-sm text-muted-foreground">
              {answered.length} of {run.questions.length} answered
            </span>
          </div>
        </form>
      </Turn>
    </section>
  );
}
