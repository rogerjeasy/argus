import { render } from "@testing-library/react";
import { expect, test } from "vitest";
import { Skeleton } from "@/components/ui/skeleton";

test("renders a decorative pulsing placeholder, hidden from assistive tech", () => {
  const { container } = render(<Skeleton className="h-4 w-24" />);
  const el = container.firstElementChild;
  expect(el).toHaveAttribute("aria-hidden", "true");
  expect(el?.className).toContain("animate-pulse");
});
