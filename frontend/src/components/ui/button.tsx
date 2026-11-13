/**
 * Buttons and button-styled links. One component family so every action in the app
 * looks and behaves the same (focus ring, disabled state, loading spinner).
 */
import Link, { type LinkProps } from "next/link";
import type { ButtonHTMLAttributes, ReactNode } from "react";

import { Spinner } from "@/components/ui/spinner";

export type ButtonVariant = "primary" | "dark" | "white" | "secondary" | "ghost" | "danger";
export type ButtonSize = "sm" | "md" | "lg";

const VARIANTS: Record<ButtonVariant, string> = {
  /** Main call to action: pink → orange gradient. */
  primary:
    "gradient-fill text-white shadow-[var(--shadow-glow)] hover:brightness-110 hover:-translate-y-px",
  /** Strong neutral action. */
  dark: "bg-ink text-white hover:bg-ink-soft hover:-translate-y-px",
  /** For use on top of gradient backgrounds. */
  white: "bg-white text-ink shadow-[var(--shadow-card)] hover:-translate-y-px",
  secondary: "bg-surface text-ink border-2 border-line hover:border-line-strong hover:bg-sunken",
  ghost: "text-ink-soft hover:bg-sunken hover:text-ink",
  danger: "bg-surface text-danger border-2 border-line hover:bg-danger-soft",
};

const SIZES: Record<ButtonSize, string> = {
  sm: "h-9 px-4 text-sm gap-1.5",
  md: "h-11 px-5 text-sm gap-2",
  lg: "h-14 px-8 text-base gap-2",
};

/** Class string shared by <Button> and <ButtonLink>. */
export function buttonClasses(variant: ButtonVariant = "primary", size: ButtonSize = "md"): string {
  return [
    "inline-flex items-center justify-center rounded-full font-semibold whitespace-nowrap",
    "transition-all duration-150 disabled:pointer-events-none disabled:opacity-50",
    VARIANTS[variant],
    SIZES[size],
  ].join(" ");
}

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
  size?: ButtonSize;
  loading?: boolean;
}

export function Button({
  variant = "primary",
  size = "md",
  loading = false,
  disabled,
  className = "",
  children,
  type = "button",
  ...rest
}: ButtonProps) {
  return (
    <button
      type={type}
      disabled={disabled || loading}
      aria-busy={loading || undefined}
      className={`${buttonClasses(variant, size)} ${className}`}
      {...rest}
    >
      {loading ? <Spinner className="size-4" /> : null}
      {children}
    </button>
  );
}

interface ButtonLinkProps extends LinkProps {
  variant?: ButtonVariant;
  size?: ButtonSize;
  className?: string;
  children: ReactNode;
}

export function ButtonLink({
  variant = "primary",
  size = "md",
  className = "",
  children,
  ...rest
}: ButtonLinkProps) {
  return (
    <Link className={`${buttonClasses(variant, size)} ${className}`} {...rest}>
      {children}
    </Link>
  );
}
