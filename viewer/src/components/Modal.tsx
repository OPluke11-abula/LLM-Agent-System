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
      style={{ background: "rgba(5,7,11,0.72)" }}
    >
      <div className="control-surface w-[480px] p-6">
        <h3 className="mb-4 text-base font-semibold t1">{title}</h3>
        <div>{children}</div>
        <div className="mt-6 flex justify-end gap-3">
          <button
            type="button"
            onClick={onCancel}
            className="quiet-button rounded-lg px-4 py-2 text-sm font-semibold"
          >
            {cancelText}
          </button>
          <button
            type="button"
            onClick={onConfirm}
            className={`rounded-lg border px-4 py-2 text-sm font-semibold transition-colors ${
              danger
                ? "border-red-400/35 bg-red-500/12 text-red-200 hover:bg-red-500/18"
                : "primary-button"
            }`}
          >
            {confirmText}
          </button>
        </div>
      </div>
    </div>
  );
}
