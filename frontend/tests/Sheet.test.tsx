import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { Sheet, SheetClose, SheetContent, SheetTitle, SheetTrigger } from "../components/ui/sheet";

describe("Sheet", () => {
  it("is closed by default and opens when the trigger is clicked", async () => {
    render(
      <Sheet>
        <SheetTrigger>Open menu</SheetTrigger>
        <SheetContent>
          <SheetTitle>Menu</SheetTitle>
          <SheetClose>Close</SheetClose>
        </SheetContent>
      </Sheet>
    );

    expect(screen.queryByRole("button", { name: "Close" })).not.toBeInTheDocument();
    // fireEvent (not a raw DOM .click()) so React's act() wraps the state
    // update Radix's Dialog makes when it opens — a bare .click() leaves
    // that update unwrapped and React warns about it even though the
    // assertion below still passes.
    fireEvent.click(screen.getByRole("button", { name: "Open menu" }));
    await waitFor(() => expect(screen.getByRole("button", { name: "Close" })).toBeInTheDocument());
  });
});
