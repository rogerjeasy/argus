import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { Reveal } from "../components/marketing/Reveal";

describe("Reveal", () => {
  it("renders its children regardless of intersection state", () => {
    render(
      <Reveal>
        <p>Section content</p>
      </Reveal>
    );
    expect(screen.getByText("Section content")).toBeInTheDocument();
  });
});
