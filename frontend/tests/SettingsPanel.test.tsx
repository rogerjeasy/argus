import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { SettingsPanel } from "@/components/SettingsPanel";
import { useAuth } from "@/lib/auth/AuthProvider";
import { getUserSettings, updateUserSettings } from "@/lib/api/userSettings";

vi.mock("@/lib/auth/AuthProvider", () => ({
  useAuth: vi.fn(),
}));

vi.mock("@/lib/api/userSettings", () => ({
  getUserSettings: vi.fn(),
  updateUserSettings: vi.fn(),
}));

function mockUser() {
  vi.mocked(useAuth).mockReturnValue({
    user: { getIdToken: vi.fn().mockResolvedValue("fake-token") },
  } as never);
}

test("opening the panel loads the current setting, defaulted off", async () => {
  mockUser();
  vi.mocked(getUserSettings).mockResolvedValue({
    verbosity: "normal", pace: "normal", audio_perception_enabled: false,
  });

  render(<SettingsPanel />);
  fireEvent.click(screen.getByRole("button", { name: /settings/i }));

  const toggle = await screen.findByRole("switch", { name: /audio perception/i });
  expect(toggle).toHaveAttribute("aria-checked", "false");
});

test("toggling on calls updateUserSettings with audio_perception_enabled: true", async () => {
  mockUser();
  vi.mocked(getUserSettings).mockResolvedValue({
    verbosity: "normal", pace: "normal", audio_perception_enabled: false,
  });
  vi.mocked(updateUserSettings).mockResolvedValue({
    verbosity: "normal", pace: "normal", audio_perception_enabled: true,
  });

  render(<SettingsPanel />);
  fireEvent.click(screen.getByRole("button", { name: /settings/i }));
  const toggle = await screen.findByRole("switch", { name: /audio perception/i });

  fireEvent.click(toggle);

  await waitFor(() =>
    expect(vi.mocked(updateUserSettings)).toHaveBeenCalledWith("fake-token", { audio_perception_enabled: true })
  );
});

test("the description explains what audio perception does before it is ever turned on", async () => {
  mockUser();
  vi.mocked(getUserSettings).mockResolvedValue({
    verbosity: "normal", pace: "normal", audio_perception_enabled: false,
  });

  render(<SettingsPanel />);
  fireEvent.click(screen.getByRole("button", { name: /settings/i }));

  expect(await screen.findByText(/listens for concerning ambient sounds/i)).toBeInTheDocument();
  expect(screen.getByText(/never records or stores audio/i)).toBeInTheDocument();
});
