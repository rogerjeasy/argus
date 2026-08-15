"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect } from "react";

import { AuthDivider } from "@/components/auth/AuthDivider";
import { AuthShell } from "@/components/auth/AuthShell";
import { GoogleSignInButton } from "@/components/auth/GoogleSignInButton";
import { SignUpForm } from "@/components/auth/SignUpForm";
import { useAuth } from "@/lib/auth/AuthProvider";

export default function SignUpPage() {
  const router = useRouter();
  const { user, loading, signInWithGoogle } = useAuth();

  useEffect(() => {
    if (!loading && user) {
      router.replace("/app");
    }
  }, [loading, user, router]);

  return (
    <AuthShell>
      <div className="space-y-6">
        <div className="space-y-2">
          <h1 className="text-3xl font-semibold tracking-tight text-foreground">Create your account</h1>
          <p className="text-muted-foreground">Set up Argus in under a minute.</p>
        </div>
        <GoogleSignInButton loading={loading} onClick={() => void signInWithGoogle()}>
          Continue with Google
        </GoogleSignInButton>
        <AuthDivider />
        <SignUpForm onSuccess={() => router.replace("/app")} />
        <p className="text-center text-sm text-muted-foreground">
          Already have an account?{" "}
          <Link href="/sign-in" className="font-medium text-primary hover:underline">
            Sign in
          </Link>
        </p>
      </div>
    </AuthShell>
  );
}
