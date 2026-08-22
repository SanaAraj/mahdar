import { useEffect, useRef } from "react";
import { z } from "zod";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";

import { Input } from "@/components/ui/input";
import { MAX_LABEL_LENGTH } from "@/lib/config";
import { strings } from "@/lib/strings";

export const renameSchema = z.object({
  label: z.string().trim().min(1).max(MAX_LABEL_LENGTH),
});
export type RenameFormValues = z.infer<typeof renameSchema>;

export interface RenameFormProps {
  defaultLabel: string;
  ringColor: string;
  submitting: boolean;
  onSubmit: (values: RenameFormValues) => void;
  onCancel: () => void;
}

export function RenameForm({
  defaultLabel,
  ringColor,
  submitting,
  onSubmit,
  onCancel,
}: RenameFormProps) {
  const form = useForm<RenameFormValues>({
    resolver: zodResolver(renameSchema),
    defaultValues: { label: defaultLabel },
    mode: "onSubmit",
  });
  const inputRef = useRef<HTMLInputElement | null>(null);

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = form;

  const { ref: fieldRef, ...fieldProps } = register("label", {
    onBlur: () => {
      handleSubmit(onSubmit)();
    },
  });

  useEffect(() => {
    inputRef.current?.focus();
    inputRef.current?.select();
  }, []);

  return (
    <form
      className="flex items-center gap-2"
      onSubmit={handleSubmit(onSubmit)}
      noValidate
    >
      <Input
        type="text"
        maxLength={MAX_LABEL_LENGTH}
        disabled={submitting}
        aria-label={strings.renameLabel}
        aria-invalid={errors.label ? true : undefined}
        className="h-auto min-w-[120px] rounded-full px-3 py-1 text-[13px]"
        style={{ borderColor: ringColor }}
        onKeyDown={(e) => {
          if (e.key === "Escape") {
            e.preventDefault();
            onCancel();
          }
        }}
        ref={(el) => {
          fieldRef(el);
          inputRef.current = el;
        }}
        {...fieldProps}
      />
      <span className="text-[11px] text-[var(--color-ink-soft)] whitespace-nowrap">
        {strings.renameHint}
      </span>
      {errors.label ? (
        <span role="alert" className="text-[12px] text-[var(--color-danger)]">
          {strings.renameFailed}
        </span>
      ) : null}
    </form>
  );
}
