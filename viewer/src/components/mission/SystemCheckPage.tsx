import { useCallback, useEffect, useRef, useState } from "react";
import { MISSION_API_SCHEMA_VERSION, type MissionSystemCapabilities } from "../../generated/missionContracts";
import { MissionApiError, missionApi } from "../../services/missionApi";
import { clearMissionSession, missionAuth, setBrowserSessionCredential } from "../../services/missionAuth";
import { Button, LinkButton, StatusBadge, Surface } from "../ui/primitives";

type CheckState = "idle" | "checking" | "unreachable" | "unauthorized" | "authenticated_compatible" | "authenticated_storage_unavailable" | "schema_mismatch" | "server_error" | "auth_unavailable" | "aborted";

function statusLabel(state: CheckState): string {
  return state.replaceAll("_", " ");
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
      setState(schemaCompatible ? result.mission_store_available ? "authenticated_compatible" : "authenticated_storage_unavailable" : "schema_mismatch");
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
        setError("System Check returned an unexpected failure.");
      }
    } finally {
      if (activeCheck.current === controller) activeCheck.current = null;
    }
  }, []);

  const cancelCheck = useCallback(() => activeCheck.current?.abort(), []);

  const isBrowser = missionAuth.mode === "browser";
  return <section className="flex h-full min-h-0 flex-col gap-5 overflow-auto pb-6">
    <header><p className="eyebrow-label">執行環境驗證</p><h1 className="mt-2 text-2xl font-semibold t1">系統健康診斷</h1><p className="mt-2 max-w-2xl text-sm t2">本機控制中樞唯讀健康診斷。此檢查不會調用外部模型、修改 Git 或產生交付副作用。</p></header>
    {!isBrowser && <Surface elevated className="max-w-2xl p-5"><p className="text-sm font-semibold t1">Tauri 任務身分驗證不可用</p><p className="mt-1 text-xs t2">P1 任務流程專為瀏覽器模式設計。原生桌面端無須驗證即可直接使用其他中樞功能。</p></Surface>}
    {isBrowser && <Surface elevated className="max-w-2xl p-5"><p className="text-sm font-semibold t1">瀏覽器開發者 Session 憑證</p><p className="mt-1 text-xs t2">輸入本分頁之開發金鑰。僅保存在記憶體中，絕不寫入 localStorage 或日誌。</p><label className="mt-4 grid gap-2 text-sm font-semibold t1">Session 憑證<input aria-label="Browser session credential" type="password" value={credential} onChange={(event) => setCredential(event.target.value)} className="rounded-lg border bg-[var(--bg-muted)] px-3 py-2.5 text-sm font-normal t1 outline-none focus:ring-2" style={{ borderColor: "var(--border-c)", outlineColor: "var(--accent)" }} autoComplete="off" /></label><div className="mt-4 flex flex-wrap gap-3"><Button variant="primary" onClick={() => { setBrowserSessionCredential(credential); void check(); }}>驗證 Session</Button>{missionAuth.configured && <Button onClick={() => { clearMissionSession(); setCredential(""); setCapabilities(null); setState("unauthorized"); }}>清除 Session</Button>}</div></Surface>}
    <Surface elevated className="max-w-3xl p-5"><div className="flex flex-wrap items-center justify-between gap-4"><div><p className="text-sm font-semibold t1">任務 API 服務契約</p><p className="mt-1 font-mono text-xs t3">GET /v1/system/capabilities</p></div><StatusBadge tone={statusTone(state)}>{statusLabel(state)}</StatusBadge></div>{error && <p className="mt-4 text-sm" style={{ color: "var(--danger)" }} role="alert">{error}</p>}<div className="mt-5 grid gap-2 border-t pt-4 text-sm" style={{ borderColor: "var(--border-c)" }}><div className="flex justify-between gap-4"><span className="t2">HTTP 狀態碼</span><span className="font-mono t1">{status ?? "—"}</span></div>{capabilities && <><div className="flex justify-between gap-4"><span className="t2">工作區就緒狀態</span><span className="t1">{capabilities.workspace_root_available ? "就緒可用" : "未就緒"}</span></div><div className="flex justify-between gap-4"><span className="t2">任務存儲庫狀態</span><span className="t1">{capabilities.mission_store_available ? "就緒可用" : "未就緒"}</span></div><div className="flex justify-between gap-4"><span className="t2">契約結構規範</span><span className="font-mono text-xs t1">{capabilities.contract_schema_version} / Viewer {MISSION_API_SCHEMA_VERSION}</span></div><div className="flex justify-between gap-4"><span className="t2">模型供應商配置</span><span className="t1">{capabilities.provider_configuration.replaceAll("_", " ")}</span></div></>}</div>{state === "checking" ? <Button className="mt-5" onClick={cancelCheck}>取消診斷</Button> : <Button className="mt-5" onClick={() => void check()}>{state === "idle" ? "執行系統診斷" : "重新執行診斷"}</Button>}{state === "authenticated_compatible" && <LinkButton to="/missions" variant="primary" className="ml-3">前往任務清單</LinkButton>}{state === "authenticated_storage_unavailable" && <p className="mt-4 text-xs t2">身分驗證成功，但任務存儲庫離線。暫無法執行需要持久化的任務。</p>}</Surface>
  </section>;
}
