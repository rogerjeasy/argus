const MESSAGES: Record<string, string> = {
  "auth/email-already-in-use": "An account with that email already exists. Try signing in instead.",
  "auth/invalid-credential": "That email or password doesn't look right. Please try again.",
  "auth/wrong-password": "That email or password doesn't look right. Please try again.",
  "auth/user-not-found": "That email or password doesn't look right. Please try again.",
  "auth/weak-password": "Choose a password with at least 8 characters, including a letter and a number.",
  "auth/too-many-requests": "Too many attempts. Please wait a moment and try again.",
  "auth/invalid-email": "Enter a valid email address.",
};

const FALLBACK = "Something went wrong. Please try again.";

export function firebaseAuthErrorMessage(error: unknown): string {
  const code =
    typeof error === "object" && error !== null && "code" in error
      ? String((error as { code: unknown }).code)
      : undefined;
  return (code && MESSAGES[code]) || FALLBACK;
}
