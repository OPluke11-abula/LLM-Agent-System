import type { PeripheralDevice } from "../../hooks/useAmbientCompanion";

interface CompanionPeripheralBadgeProps {
  devices: PeripheralDevice[];
  alerts?: string[];
}

function getKindIcon(kind: string): string {
  switch (kind) {
    case "headset":
      return "🎧";
    case "mouse":
      return "🖱️";
    case "keyboard":
      return "⌨️";
    case "controller":
      return "🎮";
    default:
      return "🔋";
  }
}

export function CompanionPeripheralBadge({ devices, alerts = [] }: CompanionPeripheralBadgeProps) {
  if (!devices || devices.length === 0) {
    return null;
  }

  return (
    <div
      data-testid="companion-peripherals-badge-container"
      className="flex flex-col gap-1.5 pt-1 border-t border-[var(--border-c)]"
    >
      <div className="flex items-center justify-between text-[10px] text-[var(--t3)] font-mono">
        <span className="flex items-center gap-1">
          <span className="h-1.5 w-1.5 rounded-full bg-emerald-400"></span>
          <span>周邊設備電量</span>
        </span>
        <span className="text-[9px] text-[var(--t3)]">HaloBattery</span>
      </div>

      <div className="flex flex-wrap items-center gap-1.5">
        {devices.map((device) => {
          const isLow = device.online && !device.charging && device.level !== null && device.level <= 15;
          const isCharging = device.charging;

          let colorClasses = "bg-[var(--bg-muted)] border-[var(--border-c)] text-[var(--t2)]";
          if (isLow) {
            colorClasses = "bg-amber-950/40 border-amber-600/50 text-amber-300 animate-pulse";
          } else if (isCharging) {
            colorClasses = "bg-emerald-950/40 border-emerald-600/40 text-emerald-300";
          }

          return (
            <div
              key={`${device.name}-${device.kind}`}
              title={device.text || `${device.name}: ${device.level ?? "?"}%`}
              data-testid={`peripheral-item-${device.kind}`}
              className={`flex items-center gap-1 px-2 py-0.5 rounded-md border text-[10px] font-mono select-none transition-colors ${colorClasses}`}
            >
              <span>{getKindIcon(device.kind)}</span>
              <span className="truncate max-w-[80px]">{device.name.split(" ")[0]}</span>
              <span className="font-bold">
                {device.level !== null ? `${device.level}%` : "--"}
              </span>
              {isCharging && <span className="text-[9px] text-emerald-400 font-bold">⚡</span>}
            </div>
          );
        })}
      </div>

      {alerts.length > 0 && (
        <div
          data-testid="peripheral-alert-banner"
          className="text-[10px] text-amber-400/90 bg-amber-950/30 border border-amber-800/40 px-2 py-1 rounded"
        >
          {alerts[0]}
        </div>
      )}
    </div>
  );
}
