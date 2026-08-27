"use client";

import { useCallback, useEffect, useState } from "react";
import { Phone } from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useIdToken } from "@/lib/auth/useIdToken";
import { getTrustedContact, updateTrustedContact, type TrustedContact } from "@/lib/api/trustedContact";

type LoadState = "loading" | "loaded" | "error";

export default function ContactsPage() {
  const token = useIdToken();
  const [contact, setContact] = useState<TrustedContact | null>(null);
  const [name, setName] = useState("");
  const [phone, setPhone] = useState("");
  const [loadState, setLoadState] = useState<LoadState>("loading");
  const [saving, setSaving] = useState(false);

  const load = useCallback(() => {
    if (!token) return;
    setLoadState("loading");
    getTrustedContact(token)
      .then((next) => {
        setContact(next);
        setName(next?.name ?? "");
        setPhone(next?.phone_number ?? "");
        setLoadState("loaded");
      })
      .catch((err) => {
        console.error(err);
        setLoadState("error");
      });
  }, [token]);

  useEffect(() => {
    load();
  }, [load]);

  const save = async () => {
    if (!token || !name || !phone) return;
    setSaving(true);
    try {
      const saved = await updateTrustedContact(token, { name, phone_number: phone });
      setContact(saved);
    } finally {
      setSaving(false);
    }
  };

  if (loadState === "loading") {
    return (
      <Card>
        <CardHeader>
          <Skeleton className="h-6 w-48" />
        </CardHeader>
        <CardContent>
          <Skeleton className="h-11 w-full" />
          <Skeleton className="h-11 w-full" />
        </CardContent>
      </Card>
    );
  }

  if (loadState === "error") {
    return (
      <Card>
        <CardContent className="items-center text-center">
          <p className="text-sm text-muted-foreground">Your trusted contact couldn&apos;t be loaded.</p>
          <Button variant="outline" onClick={load}>
            Try again
          </Button>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Trusted contact</CardTitle>
        <CardDescription>
          Who Argus texts and calls if it ever needs to escalate on your behalf — for example, if a
          concerning sound is detected and confirmed by a second signal.
        </CardDescription>
      </CardHeader>
      <CardContent>
        {!contact ? (
          <div className="flex flex-col items-center gap-2 py-6 text-center">
            <Phone className="h-8 w-8 text-muted-foreground" aria-hidden />
            <p className="text-sm text-muted-foreground">No trusted contact set yet.</p>
          </div>
        ) : null}
        <div className="flex flex-col gap-2">
          <Label htmlFor="trusted-contact-name">Name</Label>
          <Input id="trusted-contact-name" value={name} onChange={(e) => setName(e.target.value)} aria-label="Trusted contact name" />
        </div>
        <div className="flex flex-col gap-2">
          <Label htmlFor="trusted-contact-phone">Phone number</Label>
          <Input
            id="trusted-contact-phone"
            type="tel"
            value={phone}
            onChange={(e) => setPhone(e.target.value)}
            aria-label="Trusted contact phone number"
          />
        </div>
        <Button onClick={save} disabled={saving || !name || !phone} variant="default">
          {contact ? "Save changes" : "Add contact"}
        </Button>
      </CardContent>
    </Card>
  );
}
