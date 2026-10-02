type ContextMenuItem = {
  id: string;
  label: string;
  onClick: () => void;
  tone?: "default" | "danger";
  separatorBefore?: boolean;
};

type ContextMenuProps = {
  x: number;
  y: number;
  items: ContextMenuItem[];
  onClose: () => void;
};

export function ContextMenu({ x, y, items, onClose }: ContextMenuProps) {
  const left = Math.min(x, window.innerWidth - 240);
  const top = Math.min(y, window.innerHeight - 320);

  return (
    <div className="fixed inset-0 z-40">
      <button
        type="button"
        aria-label="Close context menu"
        className="absolute inset-0 cursor-default border-0 bg-transparent p-0"
        onClick={onClose}
        onContextMenu={(event) => event.preventDefault()}
      />
      <div
        className="control-surface absolute w-56 p-1.5"
        style={{
          left,
          top,
        }}
        onClick={(event) => event.stopPropagation()}
      >
        {items.map((item) => (
          <div key={item.id}>
            {item.separatorBefore && <div className="my-2 border-t" style={{ borderColor: "var(--border-c)" }} />}
            <button
              type="button"
              onClick={item.onClick}
              className="flex w-full items-center rounded-lg px-3 py-2.5 text-left text-sm font-medium transition-colors hover:bg-white/5"
              style={{ color: item.tone === "danger" ? "var(--danger)" : "var(--t1)" }}
            >
              {item.label}
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}
