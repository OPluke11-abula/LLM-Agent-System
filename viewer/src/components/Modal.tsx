import type { ReactNode } from "react";

type ModalProps = {
  title: string;
  children: ReactNode;
  onConfirm: () => void;
  onCancel: () => void;
  confirmText: string;
  cancelText: string;
  danger?: boolean;
};

export function Modal({
  title,
  children,
  onConfirm,
  onCancel,
  confirmText,
  cancelText,
  danger = false,
}: ModalProps) {
  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center"
      style={{ background: "rgba(0,0,0,0.65)", backdropFilter: "blur(4px)" }}
    >
      <div
        className="w-[480px] rounded-2xl border p-6 shadow-2xl panel-bg"
        style={{ borderColor: "var(--border-c)" }}
      >
        <h3 className="mb-4 text-base font-bold t1">{title}</h3>
        <div>{children}</div>
        <div className="mt-6 flex justify-end gap-3">
          <button
            type="button"
            onClick={onCancel}
            className="rounded-lg border px-4 py-2 text-sm font-bold transition-colors t2"
            style={{ borderColor: "var(--border-c)", background: "var(--bg-card)" }}
          >
            {cancelText}
          </button>
          <button
            type="button"
            onClick={onConfirm}
            className={`rounded-lg px-4 py-2 text-sm font-bold text-white transition-colors ${
              danger ? "bg-red-600 hover:bg-red-500" : "bg-sky-600 hover:bg-sky-500"
            }`}
          >
            {confirmText}
          </button>
        </div>
      </div>
    </div>
  );
}
