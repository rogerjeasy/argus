import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { FramingStatus } from "@/components/FramingStatus";

describe("FramingStatus", () => {
  it("renders a warning badge when confidence is low", () => {
    render(<FramingStatus confidenceLow />);
    expect(screen.getByText(/confidence low/i)).toBeInTheDocument();
  });

  it("renders nothing when confidence is not low", () => {
    const { container } = render(<FramingStatus confidenceLow={false} />);
    expect(container).toBeEmptyDOMElement();
  });
});
