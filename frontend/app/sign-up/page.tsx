"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { AuthDivider } from "@/components/auth/AuthDivider";
import { AuthFormError } from "@/components/auth/AuthFormError";
import { AuthShell } from "@/components/auth/AuthShell";
import { GoogleSignInButton } from "@/components/auth/GoogleSignInButton";
import { SignUpForm } from "@/components/auth/SignUpForm";
import { useAuth } from "@/lib/auth/AuthProvider";
import { firebaseAuthErrorMessage } from "@/lib/auth/errors";

export default function SignUpPage() {
  const router = useRouter();
  const { user, loading, signInWithGoogle } = useAuth();
  const [googleLoading, setGoogleLoading] = useState(false);
  const [googleError, setGoogleError] = useState<string | null>(null);

  useEffect(() => {
    if (!loading && user) {
      router.replace("/app");
    }
  }, [loading, user, router]);

  const handleGoogleSignIn = async () => {
    setGoogleError(null);
    setGoogleLoading(true);
    try {
      await signInWithGoogle();
    } catch (error) {
      setGoogleError(firebaseAuthErrorMessage(error));
    } finally {
      setGoogleLoading(false);
    }
  };

  return (
    <AuthShell>
      <div className="space-y-6">
        <div className="space-y-2">
          <h1 className="text-3xl font-semibold tracking-tight text-foreground">Create your account</h1>
          <p className="text-muted-foreground">Set up Argus in under a minute.</p>
        </div>
        <GoogleSignInButton loading={googleLoading} onClick={() => void handleGoogleSignIn()}>
          Continue with Google
        </GoogleSignInButton>
        <AuthFormError message={googleError} />
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
