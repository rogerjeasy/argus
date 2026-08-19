import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { SettingsPanel } from "@/components/SettingsPanel";
import { useAuth } from "@/lib/auth/AuthProvider";
import { getUserSettings, updateUserSettings } from "@/lib/api/userSettings";
import { getTrustedContact, updateTrustedContact } from "@/lib/api/trustedContact";

vi.mock("@/lib/auth/AuthProvider", () => ({
  useAuth: vi.fn(),
}));

vi.mock("@/lib/api/userSettings", () => ({
  getUserSettings: vi.fn(),
  updateUserSettings: vi.fn(),
}));

vi.mock("@/lib/api/trustedContact", () => ({
  getTrustedContact: vi.fn(),
  updateTrustedContact: vi.fn(),
}));

function mockUser() {
  vi.mocked(useAuth).mockReturnValue({
    user: { getIdToken: vi.fn().mockResolvedValue("fake-token") },
  } as never);
}

test("opening the panel loads the current setting, defaulted off", async () => {
  mockUser();
  vi.mocked(getUserSettings).mockResolvedValue({
    verbosity: "normal", pace: "normal", audio_perception_enabled: false, language_preference: "en",
  });

  render(<SettingsPanel />);
  fireEvent.click(screen.getByRole("button", { name: /settings/i }));

  const toggle = await screen.findByRole("switch", { name: /audio perception/i });
  expect(toggle).toHaveAttribute("aria-checked", "false");
});

test("toggling on calls updateUserSettings with audio_perception_enabled: true", async () => {
  mockUser();
  vi.mocked(getUserSettings).mockResolvedValue({
    verbosity: "normal", pace: "normal", audio_perception_enabled: false, language_preference: "en",
  });
  vi.mocked(updateUserSettings).mockResolvedValue({
    verbosity: "normal", pace: "normal", audio_perception_enabled: true, language_preference: "en",
  });

  render(<SettingsPanel />);
  fireEvent.click(screen.getByRole("button", { name: /settings/i }));
  const toggle = await screen.findByRole("switch", { name: /audio perception/i });

  fireEvent.click(toggle);

  await waitFor(() =>
    expect(vi.mocked(updateUserSettings)).toHaveBeenCalledWith("fake-token", { audio_perception_enabled: true })
  );
});

test("lets the user change language preference", async () => {
  mockUser();
  vi.mocked(getUserSettings).mockResolvedValue({
    verbosity: "normal", pace: "normal", audio_perception_enabled: false, language_preference: "en",
  });

  render(<SettingsPanel />);
  fireEvent.click(screen.getByRole("button", { name: /settings/i }));
  await screen.findByLabelText("Language");

  fireEvent.change(screen.getByLabelText("Language"), { target: { value: "ar" } });

  await waitFor(() =>
    expect(vi.mocked(updateUserSettings)).toHaveBeenCalledWith("fake-token", { language_preference: "ar" })
  );
});

test("the description explains what audio perception does before it is ever turned on", async () => {
  mockUser();
  vi.mocked(getUserSettings).mockResolvedValue({
    verbosity: "normal", pace: "normal", audio_perception_enabled: false, language_preference: "en",
  });

  render(<SettingsPanel />);
  fireEvent.click(screen.getByRole("button", { name: /settings/i }));

  expect(await screen.findByText(/listens for concerning ambient sounds/i)).toBeInTheDocument();
  expect(screen.getByText(/never records or stores audio/i)).toBeInTheDocument();
});

test("loads and displays an existing trusted contact", async () => {
  mockUser();
  vi.mocked(getUserSettings).mockResolvedValue({
    verbosity: "normal", pace: "normal", audio_perception_enabled: false, language_preference: "en",
  });
  vi.mocked(getTrustedContact).mockResolvedValue({ name: "Jamie", phone_number: "+15559990000" });

  render(<SettingsPanel />);
  fireEvent.click(screen.getByRole("button", { name: /settings/i }));

  expect(await screen.findByDisplayValue("Jamie")).toBeInTheDocument();
  expect(screen.getByDisplayValue("+15559990000")).toBeInTheDocument();
});

test("saving the trusted contact calls updateTrustedContact with both fields", async () => {
  mockUser();
  vi.mocked(getUserSettings).mockResolvedValue({
    verbosity: "normal", pace: "normal", audio_perception_enabled: false, language_preference: "en",
  });
  vi.mocked(getTrustedContact).mockResolvedValue(null);
  vi.mocked(updateTrustedContact).mockResolvedValue({ name: "Jamie", phone_number: "+15559990000" });

  render(<SettingsPanel />);
  fireEvent.click(screen.getByRole("button", { name: /settings/i }));
  await screen.findByLabelText("Trusted contact name");

  fireEvent.change(screen.getByLabelText("Trusted contact name"), { target: { value: "Jamie" } });
  fireEvent.change(screen.getByLabelText("Trusted contact phone number"), { target: { value: "+15559990000" } });
  fireEvent.click(screen.getByRole("button", { name: /save trusted contact/i }));

  await waitFor(() =>
    expect(vi.mocked(updateTrustedContact)).toHaveBeenCalledWith("fake-token", {
      name: "Jamie", phone_number: "+15559990000",
    })
  );
});
