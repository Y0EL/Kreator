"use client";

export function ConfirmDialog({
  open,
  title,
  body,
  confirmLabel = "Hapus",
  onConfirm,
  onCancel,
}: {
  open: boolean;
  title: string;
  body?: string;
  confirmLabel?: string;
  onConfirm: () => void;
  onCancel: () => void;
}) {
  if (!open) return null;
  return (
    <div
      className="fixed inset-0 z-50 flex items-end justify-center bg-black/40 p-4 sm:items-center"
      onClick={onCancel}
    >
      <div
        className="card w-full max-w-md rounded-2xl p-5"
        onClick={(e) => e.stopPropagation()}
      >
        <h3 className="text-base font-semibold text-fg">{title}</h3>
        {body && <p className="mt-2 text-sm leading-relaxed text-muted">{body}</p>}
        <div className="mt-5 flex gap-2">
          <button
            onClick={onCancel}
            className="tap flex-1 rounded-xl border border-line py-2.5 text-sm font-medium text-fg active:bg-surface"
          >
            Batal
          </button>
          <button
            onClick={onConfirm}
            className="tap flex-1 rounded-xl bg-accent py-2.5 text-sm font-semibold text-accent-fg"
          >
            {confirmLabel}
          </button>
        </div>
      </div>
    </div>
  );
}
