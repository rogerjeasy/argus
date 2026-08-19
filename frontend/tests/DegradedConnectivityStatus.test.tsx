import { render, screen } from "@testing-library/react";
import { DegradedConnectivityStatus } from "@/components/DegradedConnectivityStatus";

test("renders a warning badge when showing cached guidance", () => {
  render(<DegradedConnectivityStatus usingCachedGuidance />);
  expect(screen.getByText(/reduced confidence/i)).toBeInTheDocument();
});

test("renders nothing when guidance is current", () => {
  const { container } = render(<DegradedConnectivityStatus usingCachedGuidance={false} />);
  expect(container).toBeEmptyDOMElement();
});
