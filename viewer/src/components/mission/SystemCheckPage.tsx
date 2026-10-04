import { useCallback, useEffect, useRef, useState } from "react";
import { MISSION_API_SCHEMA_VERSION, type MissionSystemCapabilities } from "../../generated/missionContracts";
import { MissionApiError, missionApi } from "../../services/missionApi";
import { clearMissionSession, missionAuth, setBrowserSessionCredential } from "../../services/missionAuth";
import { Button, LinkButton, StatusBadge, Card, CardContent } from "../ui/primitives";
import { Activity, Key, Server, RefreshCw, CheckCircle2, AlertCircle } from "../ui/icons";

type CheckState =
  | "idle"
  | "checking"
  | "unreachable"
  | "unauthorized"
  | "authenticated_compatible"
  | "authenticated_storage_unavailable"
  | "schema_mismatch"
  | "server_error"
  | "auth_unavailable"
  | "aborted";

function statusLabel(state: CheckState): string {
  switch (state) {
    case "idle":
      return "尚未診斷";
    case "checking":
      return "正在診斷中…";
    case "authenticated_compatible":
      return "正常 · 契約相容";
    case "authenticated_storage_unavailable":
      return "存儲庫離線";
    case "schema_mismatch":
      return "契約版本不符";
    case "unauthorized":
      return "未授權 (需要 Session)";
    case "unreachable":
      return "中樞服務無法連線";
    case "server_error":
      return "伺服器異常";
    case "auth_unavailable":
      return "認證模組未啟用";
    case "aborted":
      return "診斷已終止";
    default:
      return state;
  }
}

function statusTone(state: CheckState): "success" | "warning" | "danger" | "neutral" {
  if (state === "authenticated_compatible") return "success";
  if (state === "checking" || state === "idle") return "neutral";
  if (state === "authenticated_storage_unavailable" || state === "schema_mismatch" || state === "aborted") return "warning";
  return "danger";
}

export function SystemCheckPage() {
  const [state, setState] = useState<CheckState>("idle");
  const [status, setStatus] = useState<number | null>(null);
  const [capabilities, setCapabilities] = useState<MissionSystemCapabilities | null>(null);
  const [credential, setCredential] = useState("");
  const [error, setError] = useState<string | null>(null);
  const activeCheck = useRef<AbortController | null>(null);

  useEffect(() => () => activeCheck.current?.abort(), []);

  const check = useCallback(async () => {
    activeCheck.current?.abort();
    const controller = new AbortController();
    activeCheck.current = controller;
    setState("checking");
    setError(null);
    try {
      const result = await missionApi.checkSystem(controller.signal);
      setStatus(200);
      setCapabilities(result);
      const schemaCompatible = result.contract_schema_version === MISSION_API_SCHEMA_VERSION;
      setState(
        schemaCompatible
          ? result.mission_store_available
            ? "authenticated_compatible"
            : "authenticated_storage_unavailable"
          : "schema_mismatch"
      );
    } catch (cause: unknown) {
      if (cause instanceof MissionApiError) {
        setStatus(cause.status || null);
        if (cause.code === "auth_required") setState("unauthorized");
        else if (cause.code === "network_error") setState("unreachable");
        else if (cause.code === "auth_unavailable") setState("auth_unavailable");
        else if (cause.code === "store_unavailable") setState("authenticated_storage_unavailable");
        else if (cause.code === "aborted") setState("aborted");
        else setState("server_error");
        setError(cause.message);
      } else {
        setState("server_error");
        setError("系統診斷遇到未預期的例外狀況。");
      }
    } finally {
      if (activeCheck.current === controller) activeCheck.current = null;
    }
  }, []);

  const cancelCheck = useCallback(() => activeCheck.current?.abort(), []);

  const isBrowser = missionAuth.mode === "browser";

  return (
    <div className="flex h-full min-h-0 flex-col gap-5 overflow-y-auto p-4 md:p-6" style={{ background: "var(--bg-base)" }}>
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b pb-4" style={{ borderColor: "var(--border-c)" }}>
        <div>
          <div className="flex items-center gap-2">
            <Activity className="h-4 w-4 text-[var(--accent)]" />
            <h1 className="text-lg font-semibold tracking-tight text-[var(--t1)]">
              系統健康診斷
            </h1>
            <StatusBadge tone={statusTone(state)}>{statusLabel(state)}</StatusBadge>
          </div>
          <p className="mt-1 text-xs text-[var(--t3)] leading-relaxed">
            本機控制中樞唯讀健康診斷。此檢查不會調用外部模型、修改 Git 或產生交付副作用。
          </p>
        </div>
        <div className="flex items-center gap-2">
          {state === "checking" ? (
            <Button variant="quiet" size="sm" onClick={cancelCheck}>
              取消診斷
            </Button>
          ) : (
            <Button variant="primary" size="sm" onClick={() => void check()} className="inline-flex items-center gap-1.5">
              <RefreshCw className="h-3.5 w-3.5" />
              <span>{state === "idle" ? "執行系統診斷" : "重新診斷"}</span>
            </Button>
          )}
        </div>
      </div>

      <div className="grid gap-5 lg:grid-cols-2">
        {/* API Service Contract Card */}
        <Card className="nordic-card">
          <CardContent className="p-5">
            <div className="flex items-center justify-between gap-3 border-b pb-4" style={{ borderColor: "var(--border-c)" }}>
              <div className="flex items-center gap-2.5">
                <Server className="h-4 w-4 text-zinc-400" />
                <div>
                  <h2 className="text-xs font-semibold text-[var(--t1)]">任務 API 服務契約</h2>
                  <p className="mt-0.5 font-mono text-[11px] text-[var(--t3)]">GET /v1/system/capabilities</p>
                </div>
              </div>
              <StatusBadge tone={statusTone(state)}>{statusLabel(state)}</StatusBadge>
            </div>

            {error && (
              <div className="mt-4 rounded-md border border-red-500/20 bg-red-500/10 p-3 text-xs text-red-400" role="alert">
                <div className="flex items-center gap-2 font-medium">
                  <AlertCircle className="h-3.5 w-3.5" />
                  <span>連線異常</span>
                </div>
                <p className="mt-1">{error}</p>
              </div>
            )}

            <div className="mt-4 divide-y divide-[var(--border-c)] text-xs">
              <div className="flex items-center justify-between py-2.5">
                <span className="text-[var(--t3)]">HTTP 狀態碼</span>
                <span className="font-mono font-medium text-[var(--t1)]">{status ?? "—"}</span>
              </div>
              {capabilities && (
                <>
                  <div className="flex items-center justify-between py-2.5">
                    <span className="text-[var(--t3)]">工作區就緒狀態</span>
                    <span className="font-medium text-[var(--t1)]">
                      {capabilities.workspace_root_available ? "就緒可用" : "未就緒"}
                    </span>
                  </div>
                  <div className="flex items-center justify-between py-2.5">
                    <span className="text-[var(--t3)]">任務存儲庫狀態</span>
                    <span className="font-medium text-[var(--t1)]">
                      {capabilities.mission_store_available ? "就緒可用" : "未就緒"}
                    </span>
                  </div>
                  <div className="flex items-center justify-between py-2.5">
                    <span className="text-[var(--t3)]">契約結構規範版本</span>
                    <span className="font-mono text-[11px] text-[var(--t1)]">
                      {capabilities.contract_schema_version} / Viewer {MISSION_API_SCHEMA_VERSION}
                    </span>
                  </div>
                  <div className="flex items-center justify-between py-2.5">
                    <span className="text-[var(--t3)]">模型供應商配置</span>
                    <span className="font-mono text-[11px] text-[var(--t1)]">
                      {capabilities.provider_configuration.replaceAll("_", " ")}
                    </span>
                  </div>
                </>
              )}
            </div>

            <div className="mt-5 flex flex-wrap items-center gap-3 border-t pt-4" style={{ borderColor: "var(--border-c)" }}>
              {state === "authenticated_compatible" && (
                <LinkButton to="/missions" variant="primary" size="sm">
                  前往任務清單
                </LinkButton>
              )}
              {state === "authenticated_storage_unavailable" && (
                <p className="text-xs text-amber-400">身分驗證成功，但任務存儲庫離線。暫無法執行需要持久化的任務。</p>
              )}
            </div>
          </CardContent>
        </Card>

        {/* Authentication / Mode Card */}
        <Card className="nordic-card">
          <CardContent className="p-5">
            <div className="flex items-center gap-2.5 border-b pb-4" style={{ borderColor: "var(--border-c)" }}>
              <Key className="h-4 w-4 text-zinc-400" />
              <div>
                <h2 className="text-xs font-semibold text-[var(--t1)]">
                  {isBrowser ? "瀏覽器開發者 Session 憑證" : "原生桌面端運作模式"}
                </h2>
                <p className="mt-0.5 text-[11px] text-[var(--t3)]">
                  {isBrowser ? "僅保存在暫存記憶體中，絕不寫入磁碟或日誌" : "Tauri 2 原生沙盒通訊"}
                </p>
              </div>
            </div>

            {isBrowser ? (
              <div className="mt-4 space-y-4">
                <div>
                  <label htmlFor="browser-session-credential" className="block text-xs font-medium text-[var(--t2)] mb-1.5">
                    Session 憑證
                  </label>
                  <input
                    id="browser-session-credential"
                    aria-label="Session 憑證"
                    type="password"
                    value={credential}
                    onChange={(event) => setCredential(event.target.value)}
                    placeholder="輸入本分頁之開發驗證金鑰"
                    className="w-full rounded-md border border-[var(--border-c)] bg-[var(--bg-muted)] px-3 py-2 text-xs text-[var(--t1)] outline-none focus:border-[var(--border-strong)]"
                    autoComplete="off"
                  />
                </div>

                <div className="flex flex-wrap items-center gap-2.5">
                  <Button
                    variant="primary"
                    size="sm"
                    onClick={() => {
                      setBrowserSessionCredential(credential);
                      void check();
                    }}
                  >
                    驗證 Session
                  </Button>
                  {missionAuth.configured && (
                    <Button
                      variant="quiet"
                      size="sm"
                      onClick={() => {
                        clearMissionSession();
                        setCredential("");
                        setCapabilities(null);
                        setState("unauthorized");
                      }}
                    >
                      清除 Session
                    </Button>
                  )}
                </div>
              </div>
            ) : (
              <div className="mt-4 text-xs text-[var(--t3)] leading-relaxed space-y-2">
                <div className="flex items-center gap-2 text-emerald-400 font-medium">
                  <CheckCircle2 className="h-3.5 w-3.5" />
                  <span>原生 IPC 模式就緒</span>
                </div>
                <p>
                  目前正透過 Tauri 2.0 原生沙盒與本機 Rust 後端通訊。無須額外設定 Web Session 憑證即可直接呼叫中樞系統功能。
                </p>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
