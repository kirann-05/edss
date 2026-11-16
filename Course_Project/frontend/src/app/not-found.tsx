import type { Metadata } from "next";
import Link from "next/link";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader } from "@/components/ui/card";

export const metadata: Metadata = { title: "Not found" };

// An address that matches no page: say so in the app's own style, with a way back.
export default function NotFound() {
  return (
    <main className="flex min-h-dvh items-center justify-center px-4 py-12">
      <div className="w-full max-w-md">
        <Card>
          <CardHeader>
            <p className="text-sm font-medium text-muted-foreground">Executive Decision Support System</p>
            <h1 className="font-heading text-2xl font-semibold">There is no page here</h1>
            <CardDescription className="text-base">
              The address may be mistyped, or the link may be out of date.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Button asChild className="h-11 w-full text-base">
              <Link href="/">Go to the dashboard</Link>
            </Button>
          </CardContent>
        </Card>
      </div>
    </main>
  );
}
