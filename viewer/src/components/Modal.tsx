import type { ReactNode } from "react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
  Button
} from "./ui/primitives";

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
    <Dialog open={true} onOpenChange={(open) => { if (!open) onCancel(); }}>
      <DialogContent className="w-[480px] max-w-[90vw]">
        <DialogHeader>
          <DialogTitle>{title}</DialogTitle>
        </DialogHeader>
        <div className="py-2 text-xs t2 leading-relaxed">
          {children}
        </div>
        <DialogFooter>
          <Button
            type="button"
            variant="quiet"
            onClick={onCancel}
          >
            {cancelText}
          </Button>
          <Button
            type="button"
            variant={danger ? "danger" : "primary"}
            onClick={onConfirm}
          >
            {confirmText}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
