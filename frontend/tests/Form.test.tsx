import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Form, FormControl, FormField, FormItem, FormLabel, FormMessage } from "../components/ui/form";
import { Input } from "../components/ui/input";

const schema = z.object({ email: z.string().email("Enter a valid email address.") });

function TestForm({ onValid }: { onValid: (values: z.infer<typeof schema>) => void }) {
  const form = useForm<z.infer<typeof schema>>({ resolver: zodResolver(schema), defaultValues: { email: "" } });
  return (
    <Form {...form}>
      <form onSubmit={form.handleSubmit(onValid)}>
        <FormField
          control={form.control}
          name="email"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Email</FormLabel>
              <FormControl>
                <Input {...field} />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />
        <button type="submit">Submit</button>
      </form>
    </Form>
  );
}

describe("Form primitives", () => {
  it("shows the zod error message when the field is invalid", async () => {
    render(<TestForm onValid={() => {}} />);
    fireEvent.click(screen.getByRole("button", { name: "Submit" }));
    expect(await screen.findByText("Enter a valid email address.")).toBeInTheDocument();
  });

  it("calls the submit handler with parsed values once valid", async () => {
    const onValid = vi.fn();
    render(<TestForm onValid={onValid} />);
    fireEvent.change(screen.getByLabelText("Email"), { target: { value: "a@example.com" } });
    fireEvent.click(screen.getByRole("button", { name: "Submit" }));
    await waitFor(() => expect(onValid).toHaveBeenCalledWith({ email: "a@example.com" }, expect.anything()));
  });
});
