"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect } from "react";

import { AuthDivider } from "@/components/auth/AuthDivider";
import { AuthShell } from "@/components/auth/AuthShell";
import { GoogleSignInButton } from "@/components/auth/GoogleSignInButton";
import { SignInForm } from "@/components/auth/SignInForm";
import { useAuth } from "@/lib/auth/AuthProvider";

export default function SignInPage() {
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
          <h1 className="text-3xl font-semibold tracking-tight text-foreground">Welcome back</h1>
          <p className="text-muted-foreground">Sign in to continue to Argus.</p>
        </div>
        <GoogleSignInButton loading={loading} onClick={() => void signInWithGoogle()}>
          Continue with Google
        </GoogleSignInButton>
        <AuthDivider />
        <SignInForm onSuccess={() => router.replace("/app")} />
        <p className="text-center text-sm text-muted-foreground">
          New to Argus?{" "}
          <Link href="/sign-up" className="font-medium text-primary hover:underline">
            Create an account
          </Link>
        </p>
      </div>
    </AuthShell>
  );
}
