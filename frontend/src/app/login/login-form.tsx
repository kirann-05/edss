"use client";

import { CircleAlert, FlaskConical, LoaderCircle } from "lucide-react";
import { useRouter, useSearchParams } from "next/navigation";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Separator } from "@/components/ui/separator";
import { ApiError } from "@/lib/api/client";
import { useDemoLogin, useDemoUsers, useLogin } from "@/lib/api/queries";
import { safeNext } from "@/lib/navigation";
import { ROLE_LABEL } from "@/lib/roles";

export function LoginForm() {
  const router = useRouter();
  const destination = safeNext(useSearchParams().get("next"));
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  const login = useLogin();
  const demoLogin = useDemoLogin();
  const demoUsers = useDemoUsers();

  const arrive = () => router.replace(destination);
  const busy = login.isPending || demoLogin.isPending;
  const failure = login.error ?? demoLogin.error;

  return (
    <Card>
      <CardHeader>
        <p className="text-sm font-medium text-muted-foreground">Executive Decision Support System</p>
        <h1 className="font-heading text-2xl font-semibold">Sign in</h1>
        <CardDescription className="text-base">
          Review institution KPIs and decision briefs.
        </CardDescription>
      </CardHeader>
      <CardContent className="flex flex-col gap-6">
        <form
          className="flex flex-col gap-4"
          onSubmit={(event) => {
            event.preventDefault();
            login.mutate({ email, password }, { onSuccess: arrive });
          }}
        >
          <div className="flex flex-col gap-2">
            <Label htmlFor="email" className="text-base">
              Email
            </Label>
            <Input
              id="email"
              type="email"
              autoComplete="username"
              required
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              className="h-11 text-base"
            />
          </div>
          <div className="flex flex-col gap-2">
            <Label htmlFor="password" className="text-base">
              Password
            </Label>
            <Input
              id="password"
              type="password"
              autoComplete="current-password"
              required
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              className="h-11 text-base"
            />
          </div>

          {failure && (
            <p role="alert" className="flex items-start gap-2 text-base text-critical-ink">
              <CircleAlert aria-hidden className="mt-0.5 size-5 shrink-0" />
              {failure instanceof ApiError && failure.status === 401
                ? "Those details do not match an account. Check the email and password and try again."
                : failure instanceof ApiError && failure.status === 429
                  ? failure.message // the server says how long to wait
                  : "Sign in is not available right now. Try again in a moment."}
            </p>
          )}

          <Button type="submit" size="lg" className="h-11 text-base" disabled={busy}>
            {login.isPending && <LoaderCircle aria-hidden className="size-4 animate-spin" />}
            {login.isPending ? "Signing in" : "Sign in"}
          </Button>
        </form>

        {demoUsers.data && (
          <>
            <Separator />
            <section aria-labelledby="demo-heading" className="flex flex-col gap-3">
              <div className="flex items-center gap-2">
                <FlaskConical aria-hidden className="size-4 text-muted-foreground" />
                <h2 id="demo-heading" className="text-base font-medium">
                  Demo mode
                </h2>
              </div>
              <p className="text-sm text-muted-foreground">
                Synthetic data. Choose a role to sign in without a password.
              </p>
              <ul className="grid grid-cols-2 gap-2">
                {demoUsers.data.map((user) => (
                  <li key={user.email}>
                    <Button
                      type="button"
                      variant="outline"
                      className="h-auto w-full flex-col items-start gap-0.5 px-3 py-2 text-left"
                      disabled={busy}
                      onClick={() => demoLogin.mutate(user.email, { onSuccess: arrive })}
                    >
                      <span className="text-sm font-medium">
                        {ROLE_LABEL[user.role]}
                        {user.dept_code ? ` (${user.dept_code})` : ""}
                      </span>{" "}
                      <span className="text-xs font-normal text-muted-foreground">{user.name}</span>
                    </Button>
                  </li>
                ))}
              </ul>
            </section>
          </>
        )}
      </CardContent>
    </Card>
  );
}
