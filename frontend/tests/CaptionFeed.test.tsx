import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { CaptionFeed } from "../components/marketing/CaptionFeed";

describe("CaptionFeed", () => {
  it("renders each caption line as real, readable text, with a live indicator where flagged", () => {
    render(
      <CaptionFeed
        lines={[
          { speaker: "argus", text: "Platform four, this way." },
          { speaker: "argus", text: "Platform changed to seven, confirmed.", live: true },
        ]}
      />
    );
    expect(screen.getByText("Platform four, this way.")).toBeInTheDocument();
    expect(screen.getByText("Platform changed to seven, confirmed.")).toBeInTheDocument();
    expect(screen.getByText("live")).toBeInTheDocument();
  });
});
