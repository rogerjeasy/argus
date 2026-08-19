import { render, screen } from "@testing-library/react";
import { ConnectionStatus } from "@/components/ConnectionStatus";

test("renders a distinct badge for each connection status, including reconnecting", () => {
  const { rerender } = render(<ConnectionStatus status="idle" />);
  expect(screen.getByText(/not connected/i)).toBeInTheDocument();

  rerender(<ConnectionStatus status="connecting" />);
  expect(screen.getByText(/connecting/i)).toBeInTheDocument();

  rerender(<ConnectionStatus status="reconnecting" />);
  expect(screen.getByText(/reconnecting/i)).toBeInTheDocument();

  rerender(<ConnectionStatus status="connected" />);
  expect(screen.getByText(/^connected$/i)).toBeInTheDocument();

  rerender(<ConnectionStatus status="error" />);
  expect(screen.getByText(/connection error/i)).toBeInTheDocument();
});
