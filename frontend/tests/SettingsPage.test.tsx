import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { beforeEach, expect, test, vi } from "vitest";
import SettingsPage from "@/app/app/settings/page";
import { useIdToken } from "@/lib/auth/useIdToken";
import { getUserSettings, updateUserSettings } from "@/lib/api/userSettings";

vi.mock("@/lib/auth/useIdToken", () => ({ useIdToken: vi.fn() }));
vi.mock("@/lib/api/userSettings", () => ({
  getUserSettings: vi.fn(),
  updateUserSettings: vi.fn(),
}));

const SETTINGS = { verbosity: "normal" as const, pace: "normal" as const, audio_perception_enabled: false, language_preference: "en" };

beforeEach(() => {
  vi.mocked(useIdToken).mockReturnValue("fake-token");
});

test("shows a loading skeleton before settings resolve, then the real fields", async () => {
  let resolve!: (value: typeof SETTINGS) => void;
  vi.mocked(getUserSettings).mockReturnValue(new Promise((r) => { resolve = r; }));

  render(<SettingsPage />);
  expect(screen.queryByLabelText("Verbosity")).not.toBeInTheDocument();

  resolve(SETTINGS);
  expect(await screen.findByLabelText("Verbosity")).toBeInTheDocument();
});

test("shows a calm retry affordance when settings fail to load", async () => {
  vi.mocked(getUserSettings).mockRejectedValue(new Error("network down"));

  render(<SettingsPage />);

  expect(await screen.findByRole("button", { name: /try again/i })).toBeInTheDocument();
  expect(screen.queryByLabelText("Verbosity")).not.toBeInTheDocument();
});

test("retrying after an error re-fetches and renders the fields", async () => {
  vi.mocked(getUserSettings).mockRejectedValueOnce(new Error("network down"));
  vi.mocked(getUserSettings).mockResolvedValueOnce(SETTINGS);

  render(<SettingsPage />);
  fireEvent.click(await screen.findByRole("button", { name: /try again/i }));

  expect(await screen.findByLabelText("Verbosity")).toBeInTheDocument();
});

test("changing verbosity updates optimistically and calls updateUserSettings", async () => {
  vi.mocked(getUserSettings).mockResolvedValue(SETTINGS);
  vi.mocked(updateUserSettings).mockResolvedValue({ ...SETTINGS, verbosity: "terse" });

  render(<SettingsPage />);
  fireEvent.change(await screen.findByLabelText("Verbosity"), { target: { value: "terse" } });

  expect(screen.getByLabelText("Verbosity")).toHaveValue("terse");
  await waitFor(() => expect(vi.mocked(updateUserSettings)).toHaveBeenCalledWith("fake-token", { verbosity: "terse" }));
});

test("changing pace calls updateUserSettings", async () => {
  vi.mocked(getUserSettings).mockResolvedValue(SETTINGS);
  vi.mocked(updateUserSettings).mockResolvedValue({ ...SETTINGS, pace: "fast" });

  render(<SettingsPage />);
  fireEvent.change(await screen.findByLabelText("Pace"), { target: { value: "fast" } });

  await waitFor(() => expect(vi.mocked(updateUserSettings)).toHaveBeenCalledWith("fake-token", { pace: "fast" }));
});

test("toggling audio perception calls updateUserSettings", async () => {
  vi.mocked(getUserSettings).mockResolvedValue(SETTINGS);
  vi.mocked(updateUserSettings).mockResolvedValue({ ...SETTINGS, audio_perception_enabled: true });

  render(<SettingsPage />);
  fireEvent.click(await screen.findByRole("switch", { name: /audio perception/i }));

  await waitFor(() =>
    expect(vi.mocked(updateUserSettings)).toHaveBeenCalledWith("fake-token", { audio_perception_enabled: true })
  );
});

test("changing language calls updateUserSettings", async () => {
  vi.mocked(getUserSettings).mockResolvedValue(SETTINGS);
  vi.mocked(updateUserSettings).mockResolvedValue({ ...SETTINGS, language_preference: "ar" });

  render(<SettingsPage />);
  fireEvent.change(await screen.findByLabelText("Language"), { target: { value: "ar" } });

  await waitFor(() =>
    expect(vi.mocked(updateUserSettings)).toHaveBeenCalledWith("fake-token", { language_preference: "ar" })
  );
});

test("the audio perception description explains what it does before it is ever turned on", async () => {
  vi.mocked(getUserSettings).mockResolvedValue(SETTINGS);

  render(<SettingsPage />);

  expect(await screen.findByText(/listens for concerning ambient sounds/i)).toBeInTheDocument();
  expect(screen.getByText(/never records or stores audio/i)).toBeInTheDocument();
});
