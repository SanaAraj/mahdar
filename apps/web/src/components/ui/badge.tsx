import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";

import { cn } from "@/lib/utils";

const badgeVariants = cva(
  "inline-flex items-center rounded-full border px-3 py-0.5 text-xs font-semibold transition-colors focus:outline-none",
  {
    variants: {
      variant: {
        default: "border-[var(--color-accent-ring)] bg-[var(--color-accent-ring)] text-[var(--color-accent-dark)]",
        secondary: "border-[var(--color-line)] bg-[var(--color-surface)] text-[var(--color-ink)]",
        danger: "border-transparent bg-[var(--color-danger-soft)] text-[var(--color-danger)]",
        warn: "border-transparent bg-[var(--color-warn-soft)] text-[var(--color-warn-ink)]",
        success: "border-transparent bg-[var(--color-accent-soft)] text-[var(--color-accent-dark)]",
        outline: "border-[var(--color-line)] bg-transparent text-[var(--color-ink)]",
      },
    },
    defaultVariants: {
      variant: "default",
    },
  },
);

export interface BadgeProps
  extends React.HTMLAttributes<HTMLSpanElement>,
    VariantProps<typeof badgeVariants> {}

const Badge = React.forwardRef<HTMLSpanElement, BadgeProps>(
  ({ className, variant, ...props }, ref) => (
    <span ref={ref} className={cn(badgeVariants({ variant }), className)} {...props} />
  ),
);
Badge.displayName = "Badge";

export { Badge, badgeVariants };
