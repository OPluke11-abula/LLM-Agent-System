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
    <div className="fixed inset-0 z-40" onClick={onClose} onContextMenu={(event) => event.preventDefault()}>
      <div
        className="absolute w-56 rounded-2xl border p-2 shadow-2xl"
        style={{
          left,
          top,
          background: "rgba(8,15,29,0.94)",
          borderColor: "var(--border-c)",
          backdropFilter: "blur(20px)",
        }}
        onClick={(event) => event.stopPropagation()}
      >
        {items.map((item) => (
          <div key={item.id}>
            {item.separatorBefore && <div className="my-2 border-t" style={{ borderColor: "var(--border-c)" }} />}
            <button
              type="button"
              onClick={item.onClick}
              className="flex w-full items-center rounded-xl px-3 py-2.5 text-left text-sm font-semibold transition-colors hover:bg-white/5"
              style={{ color: item.tone === "danger" ? "#fca5a5" : "var(--t1)" }}
            >
              {item.label}
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}
