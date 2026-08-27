import type { ButtonHTMLAttributes } from "react";

type Variant = "primary" | "dark" | "ghost" | "danger";

const VARIANTS: Record<Variant, string> = {
  primary: "btn-primary",
  dark: "btn-dark",
  ghost: "btn-ghost",
  danger: "btn-danger",
};

export function Button({
  variant = "primary",
  size,
  className = "",
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & { variant?: Variant; size?: "sm" }) {
  return (
    <button
      className={`${VARIANTS[variant]} ${size === "sm" ? "btn-sm" : ""} ${className}`}
      {...props}
    />
  );
}
