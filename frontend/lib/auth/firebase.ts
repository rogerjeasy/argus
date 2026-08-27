import { type FirebaseOptions, getApp, getApps, initializeApp } from "firebase/app";
import { type Auth, getAuth } from "firebase/auth";

const firebaseConfig: FirebaseOptions = {
  apiKey: process.env.NEXT_PUBLIC_FIREBASE_API_KEY,
  authDomain: process.env.NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN,
  projectId: process.env.NEXT_PUBLIC_FIREBASE_PROJECT_ID,
};

let cachedAuth: Auth | undefined;

/**
 * Firebase Auth is only ever touched from the browser — inside effects and
 * event handlers. Initializing it lazily (rather than at module load) keeps
 * `getAuth()` out of the server prerender pass, where a partial or absent
 * NEXT_PUBLIC_FIREBASE_* config would otherwise throw and fail the build.
 */
export function getFirebaseAuth(): Auth {
  if (!cachedAuth) {
    const app = getApps().length > 0 ? getApp() : initializeApp(firebaseConfig);
    cachedAuth = getAuth(app);
  }
  return cachedAuth;
}
