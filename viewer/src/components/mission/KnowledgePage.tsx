import { LinkButton, Surface } from "../ui/primitives";

export function KnowledgePage() {
  return <section className="flex h-full min-h-0 flex-col gap-5 overflow-auto pb-6"><header><p className="eyebrow-label">專案知識庫</p><h1 className="mt-2 text-2xl font-semibold t1">專案知識</h1><p className="mt-2 max-w-2xl text-sm t2">持久化知識記錄、Obsidian 拓撲與架構決策之可信存儲空間。</p></header><Surface elevated className="p-8 text-center"><p className="text-lg font-semibold t1">尚無外部知識庫連線</p><p className="mx-auto mt-2 max-w-lg text-sm t2">目前契約支援任務歷史、驗證證據與審計收據之雙向同步。絕不虛構或模擬未驗證知識。</p><LinkButton to="/missions" className="mt-5 inline-flex">返回任務清單</LinkButton></Surface></section>;
}
