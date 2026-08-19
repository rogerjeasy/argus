import { render, screen, fireEvent } from "@testing-library/react";
import { Select } from "@/components/ui/select";

test("renders every option and reports the chosen value", () => {
  const onChange = vi.fn();
  render(
    <Select value="en" onChange={onChange} aria-label="Language">
      <option value="en">English</option>
      <option value="ar">Arabic</option>
    </Select>
  );

  fireEvent.change(screen.getByLabelText("Language"), { target: { value: "ar" } });

  expect(onChange).toHaveBeenCalledWith("ar");
});
