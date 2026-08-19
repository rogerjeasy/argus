import { render, screen } from "@testing-library/react";
import { expect, test } from "vitest";
import { TranscriptFeed } from "@/components/TranscriptFeed";

test("shows a placeholder when there is no history yet", () => {
  render(<TranscriptFeed entries={[]} />);
  expect(screen.getByText(/will appear here/i)).toBeInTheDocument();
});

test("renders each entry's text", () => {
  render(
    <TranscriptFeed
      entries={[
        { id: 1, text: "Head to platform 4.", language: "en" },
        { id: 2, text: "Turn left.", language: "en" },
      ]}
    />
  );
  expect(screen.getByText("Head to platform 4.")).toBeInTheDocument();
  expect(screen.getByText("Turn left.")).toBeInTheDocument();
});

test("gives an RTL-language entry a right-to-left direction", () => {
  render(<TranscriptFeed entries={[{ id: 1, text: "توجه إلى الرصيف 4", language: "ar" }]} />);
  expect(screen.getByText("توجه إلى الرصيف 4")).toHaveAttribute("dir", "rtl");
});

test("the feed region is announced politely as new entries arrive", () => {
  render(<TranscriptFeed entries={[{ id: 1, text: "Head to platform 4.", language: "en" }]} />);
  expect(screen.getByLabelText("Recent guidance")).toHaveAttribute("aria-live", "polite");
});
