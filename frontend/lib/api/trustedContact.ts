import { apiFetch } from "./client";

export interface TrustedContact {
  name: string;
  phone_number: string;
}

export async function getTrustedContact(token: string): Promise<TrustedContact | null> {
  return apiFetch<TrustedContact | null>("/api/trusted-contact", { token });
}

export async function updateTrustedContact(token: string, contact: TrustedContact): Promise<TrustedContact> {
  return apiFetch<TrustedContact>("/api/trusted-contact", {
    method: "PUT",
    token,
    body: JSON.stringify(contact),
  });
}
