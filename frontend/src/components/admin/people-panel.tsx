"use client";

import { KeyRound, Pencil, Power, UserPlus } from "lucide-react";
import { useState } from "react";

import { ConfirmDialog } from "@/components/brief/decision-dialogs";
import { ErrorPanel } from "@/components/error-panel";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogClose,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { useAdminUsers, useCreateUser, useMe, useResetPassword, useUpdateUser } from "@/lib/api/queries";
import type { AdminOptions, AdminUser, Role } from "@/lib/api/types";
import { ROLE_LABEL } from "@/lib/roles";

interface PersonForm {
  name: string;
  email: string;
  role: Role;
  dept_code: string;
  school: string;
  password: string;
}

const EMPTY: PersonForm = { name: "", email: "", role: "viewer", dept_code: "", school: "", password: "" };

/** Who may sign in, and as what. An administrator manages accounts, never content. */
export function PeoplePanel({ options }: { options: AdminOptions }) {
  const me = useMe();
  const users = useAdminUsers(true);
  const update = useUpdateUser();
  const [editing, setEditing] = useState<AdminUser | "new" | null>(null);
  const [resetting, setResetting] = useState<AdminUser | null>(null);
  const [toggling, setToggling] = useState<AdminUser | null>(null);

  if (users.isPending) return <Skeleton className="h-64 w-full" />;
  if (users.isError) return <ErrorPanel error={users.error} onRetry={() => users.refetch()} what="the people list" />;

  const departments = new Map(options.departments.map((d) => [d.code, d.name]));
  const self = me.data?.user.id;

  return (
    <section aria-labelledby="people-heading" className="flex flex-col gap-3">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div className="flex flex-col gap-1">
          <h2 id="people-heading" className="text-xl font-semibold">
            People and roles
          </h2>
          <p className="text-base text-muted-foreground">
            A role decides what a person may do. A HOD sees their own department only, a Dean their school. Changes
            apply on the person&apos;s next click.
          </p>
        </div>
        <Button onClick={() => setEditing("new")}>
          <UserPlus aria-hidden data-icon="inline-start" />
          Add a person
        </Button>
      </div>
      <div className="rounded-xl border bg-card px-2">
        <Table className="text-base">
          <TableHeader>
            <TableRow>
              <TableHead className="text-base">Person</TableHead>
              <TableHead className="text-base">Role</TableHead>
              <TableHead className="text-base">Sees</TableHead>
              <TableHead className="text-base">Account</TableHead>
              <TableHead className="text-right text-base">
                <span className="sr-only">Actions</span>
              </TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {users.data.map((user) => (
              <TableRow key={user.id} className={user.active ? "align-top" : "align-top text-muted-foreground"}>
                <TableCell className="py-3 whitespace-normal">
                  <span className="font-medium">{user.name}</span>
                  {user.id === self && <span className="text-sm text-muted-foreground"> (you)</span>}
                  <span className="block text-sm text-muted-foreground">{user.email}</span>
                </TableCell>
                <TableCell className="py-3">{ROLE_LABEL[user.role]}</TableCell>
                <TableCell className="py-3 whitespace-normal">
                  {user.role === "hod"
                    ? `${user.dept_code}${departments.get(user.dept_code ?? "") ? `, ${departments.get(user.dept_code ?? "")}` : ""}`
                    : user.role === "dean"
                      ? user.school
                      : user.role === "viewer"
                        ? "Published reports only"
                        : user.role === "admin"
                          ? "Accounts and system health"
                          : "Every department"}
                </TableCell>
                <TableCell className="py-3">{user.active ? "Active" : "Switched off"}</TableCell>
                <TableCell className="py-3">
                  {/* stacked below xl, so the table fits a 1280 by 720 projector at 125 percent */}
                  <span className="flex flex-col items-end gap-1 xl:flex-row xl:justify-end">
                    <Button variant="ghost" size="sm" onClick={() => setEditing(user)} aria-label={`Edit ${user.name}`}>
                      <Pencil aria-hidden />
                      Edit
                    </Button>
                    <Button variant="ghost" size="sm" onClick={() => setResetting(user)} aria-label={`Set a new password for ${user.name}`}>
                      <KeyRound aria-hidden />
                      Password
                    </Button>
                    {user.id !== self && (
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => setToggling(user)}
                        aria-label={`${user.active ? "Switch off" : "Switch on"} ${user.name}`}
                      >
                        <Power aria-hidden />
                        {user.active ? "Switch off" : "Switch on"}
                      </Button>
                    )}
                  </span>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>

      {editing !== null && (
        <PersonDialog
          key={editing === "new" ? "new" : editing.id}
          person={editing === "new" ? null : editing}
          options={options}
          self={self ?? null}
          onClose={() => setEditing(null)}
        />
      )}
      {resetting && <PasswordDialog person={resetting} minimum={options.min_password} onClose={() => setResetting(null)} />}
      <ConfirmDialog
        open={toggling !== null}
        onOpenChange={(open) => !open && setToggling(null)}
        title={toggling ? `${toggling.active ? "Switch off" : "Switch on"} ${toggling.name}?` : ""}
        description={
          toggling?.active
            ? "They are signed out at once and cannot sign in until switched on again. Nothing they did is removed."
            : "They can sign in again with their current password."
        }
        confirmLabel={toggling?.active ? "Switch off" : "Switch on"}
        destructive={toggling?.active ?? false}
        busy={update.isPending}
        error={update.error?.message ?? null}
        onConfirm={() =>
          toggling &&
          update.mutate({ id: toggling.id, changes: { active: !toggling.active } }, { onSuccess: () => setToggling(null) })
        }
      />
    </section>
  );
}

function PersonDialog({
  person,
  options,
  self,
  onClose,
}: {
  person: AdminUser | null;
  options: AdminOptions;
  self: number | null;
  onClose: () => void;
}) {
  const create = useCreateUser();
  const update = useUpdateUser();
  const [form, setForm] = useState<PersonForm>(
    person
      ? { name: person.name, email: person.email, role: person.role, dept_code: person.dept_code ?? "", school: person.school ?? "", password: "" }
      : EMPTY,
  );
  const busy = create.isPending || update.isPending;
  const error = (person ? update.error : create.error)?.message ?? null;
  const isSelf = person !== null && person.id === self;

  const submit = () => {
    const dept_code = form.role === "hod" ? form.dept_code || null : null;
    const school = form.role === "dean" ? form.school || null : null;
    if (person) {
      const changes: Record<string, unknown> = {};
      if (form.name.trim() !== person.name) changes.name = form.name.trim();
      if (form.role !== person.role) changes.role = form.role;
      if (dept_code !== person.dept_code) changes.dept_code = dept_code;
      if (school !== person.school) changes.school = school;
      if (Object.keys(changes).length === 0) return onClose();
      update.mutate({ id: person.id, changes }, { onSuccess: onClose });
    } else {
      create.mutate(
        { name: form.name.trim(), email: form.email.trim(), role: form.role, dept_code, school, password: form.password },
        { onSuccess: onClose },
      );
    }
  };

  return (
    <Dialog open onOpenChange={(open) => !open && onClose()}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{person ? `Edit ${person.name}` : "Add a person"}</DialogTitle>
          <DialogDescription>
            {person ? "The change applies on their next click, no sign-out needed." : "They sign in with this email and password."}
          </DialogDescription>
        </DialogHeader>
        <form
          className="flex flex-col gap-4"
          onSubmit={(event) => {
            event.preventDefault();
            if (!busy) submit();
          }}
        >
          <FormField id="p-name" label="Name">
            <Input id="p-name" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} className="h-10 text-base" required />
          </FormField>
          {!person && (
            <FormField id="p-email" label="Email">
              <Input
                id="p-email"
                type="email"
                autoComplete="off"
                value={form.email}
                onChange={(e) => setForm({ ...form, email: e.target.value })}
                className="h-10 text-base"
                required
              />
            </FormField>
          )}
          <FormField id="p-role" label="Role">
            <Select value={form.role} onValueChange={(role) => setForm({ ...form, role: role as Role })} disabled={isSelf}>
              <SelectTrigger id="p-role" className="h-10 w-full text-base">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {options.roles.map((role) => (
                  <SelectItem key={role} value={role} className="text-base">
                    {ROLE_LABEL[role]}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            {isSelf && <p className="text-sm text-muted-foreground">You cannot change your own role.</p>}
          </FormField>
          {form.role === "hod" && (
            <FormField id="p-dept" label="Department">
              <Select value={form.dept_code} onValueChange={(dept_code) => setForm({ ...form, dept_code })}>
                <SelectTrigger id="p-dept" className="h-10 w-full text-base">
                  <SelectValue placeholder="Choose a department" />
                </SelectTrigger>
                <SelectContent>
                  {options.departments.map((d) => (
                    <SelectItem key={d.code} value={d.code} className="text-base">
                      {d.code}, {d.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </FormField>
          )}
          {form.role === "dean" && (
            <FormField id="p-school" label="School">
              <Select value={form.school} onValueChange={(school) => setForm({ ...form, school })}>
                <SelectTrigger id="p-school" className="h-10 w-full text-base">
                  <SelectValue placeholder="Choose a school" />
                </SelectTrigger>
                <SelectContent>
                  {options.schools.map((school) => (
                    <SelectItem key={school} value={school} className="text-base">
                      {school}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </FormField>
          )}
          {!person && (
            <FormField id="p-password" label="First password" hint={`At least ${options.min_password} characters. Tell them in person, not by email.`}>
              <Input
                id="p-password"
                type="password"
                autoComplete="new-password"
                value={form.password}
                onChange={(e) => setForm({ ...form, password: e.target.value })}
                className="h-10 text-base"
                required
                minLength={options.min_password}
              />
            </FormField>
          )}
          {error && (
            <p role="alert" className="text-base text-critical-ink">
              {error}
            </p>
          )}
          <DialogFooter>
            <DialogClose asChild>
              <Button type="button" variant="outline">
                Cancel
              </Button>
            </DialogClose>
            <Button type="submit" disabled={busy}>
              {busy ? "Saving" : person ? "Save" : "Add"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

function PasswordDialog({ person, minimum, onClose }: { person: AdminUser; minimum: number; onClose: () => void }) {
  const reset = useResetPassword();
  const [password, setPassword] = useState("");
  return (
    <Dialog open onOpenChange={(open) => !open && onClose()}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>New password for {person.name}</DialogTitle>
          <DialogDescription>Every session they have open ends at once. Tell them the new password in person.</DialogDescription>
        </DialogHeader>
        <form
          className="flex flex-col gap-4"
          onSubmit={(event) => {
            event.preventDefault();
            if (!reset.isPending) reset.mutate({ id: person.id, password }, { onSuccess: onClose });
          }}
        >
          <FormField id="new-password" label="New password" hint={`At least ${minimum} characters.`}>
            <Input
              id="new-password"
              type="password"
              autoComplete="new-password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="h-10 text-base"
              required
              minLength={minimum}
            />
          </FormField>
          {reset.isError && (
            <p role="alert" className="text-base text-critical-ink">
              {reset.error.message}
            </p>
          )}
          <DialogFooter>
            <DialogClose asChild>
              <Button type="button" variant="outline">
                Cancel
              </Button>
            </DialogClose>
            <Button type="submit" disabled={reset.isPending || password.length < minimum}>
              {reset.isPending ? "Saving" : "Set password"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

function FormField({ id, label, hint, children }: { id: string; label: string; hint?: string; children: React.ReactNode }) {
  return (
    <div className="flex flex-col gap-1.5">
      <Label htmlFor={id} className="text-base">
        {label}
      </Label>
      {children}
      {hint && <p className="text-sm text-muted-foreground">{hint}</p>}
    </div>
  );
}
