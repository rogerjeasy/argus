import { render, screen } from "@testing-library/react";
import { expect, test } from "vitest";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

test("renders a titled, described card with content", () => {
  render(
    <Card>
      <CardHeader>
        <CardTitle>Voice & Guidance</CardTitle>
        <CardDescription>How Argus speaks to you.</CardDescription>
      </CardHeader>
      <CardContent>
        <p>Body</p>
      </CardContent>
    </Card>
  );
  expect(screen.getByRole("heading", { name: "Voice & Guidance" })).toBeInTheDocument();
  expect(screen.getByText("How Argus speaks to you.")).toBeInTheDocument();
  expect(screen.getByText("Body")).toBeInTheDocument();
});
