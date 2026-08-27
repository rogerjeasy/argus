"use client";

import {
  GoogleAuthProvider,
  createUserWithEmailAndPassword,
  onAuthStateChanged,
  signInWithEmailAndPassword,
  signInWithPopup,
  signOut,
  updateProfile,
  type User,
} from "firebase/auth";
import { createContext, useContext, useEffect, useState } from "react";
import { apiFetch } from "@/lib/api/client";
import { getFirebaseAuth } from "./firebase";

type AuthContextValue = {
  user: User | null;
  loading: boolean;
  signInWithGoogle: () => Promise<void>;
  signInWithEmail: (email: string, password: string) => Promise<void>;
  signUpWithEmail: (email: string, password: string, displayName: string) => Promise<void>;
  signOutUser: () => Promise<void>;
};

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

async function syncProfile(user: User): Promise<void> {
  try {
    const token = await user.getIdToken();
    await apiFetch("/api/users/me", {
      method: "PUT",
      token,
      body: JSON.stringify({
        display_name: user.displayName,
        photo_url: user.photoURL,
      }),
    });
  } catch (error) {
    // A profile-sync hiccup must not lock someone who just successfully
    // authenticated out of the app they're trying to reach.
    console.error("Profile sync failed", error);
  }
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const unsubscribe = onAuthStateChanged(getFirebaseAuth(), (nextUser) => {
      setUser(nextUser);
      setLoading(false);
    });
    return unsubscribe;
  }, []);

  const signInWithGoogle = async () => {
    const credential = await signInWithPopup(getFirebaseAuth(), new GoogleAuthProvider());
    await syncProfile(credential.user);
  };

  const signInWithEmail = async (email: string, password: string) => {
    const credential = await signInWithEmailAndPassword(getFirebaseAuth(), email, password);
    await syncProfile(credential.user);
  };

  const signUpWithEmail = async (email: string, password: string, displayName: string) => {
    const credential = await createUserWithEmailAndPassword(getFirebaseAuth(), email, password);
    await updateProfile(credential.user, { displayName });
    await syncProfile(credential.user);
  };

  const signOutUser = async () => {
    await signOut(getFirebaseAuth());
  };

  return (
    <AuthContext.Provider
      value={{ user, loading, signInWithGoogle, signInWithEmail, signUpWithEmail, signOutUser }}
    >
      {children}
    </AuthContext.Provider>
  );
}

const PRERENDER_FALLBACK: AuthContextValue = {
  user: null,
  loading: true,
  signInWithGoogle: async () => {},
  signInWithEmail: async () => {},
  signUpWithEmail: async () => {},
  signOutUser: async () => {},
};

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (!context) {
    // On the server prerender pass React can invoke a client component
    // before the provider tree it lives under has been established. Every
    // caller already gates on `loading`, so returning the "auth not yet
    // known" state there is correct; in the browser a missing provider is a
    // real bug and still throws.
    if (typeof window === "undefined") {
      return PRERENDER_FALLBACK;
    }
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}
