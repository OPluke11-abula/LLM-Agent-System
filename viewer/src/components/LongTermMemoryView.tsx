import { useEffect, useState } from "react";
import { Modal } from "./Modal";
import { Button, MetricTile, StatusBadge, Surface } from "./ui/primitives";
import type { TranslationMessages } from "../types";

type LongTermMemoryViewProps = {
  t: TranslationMessages;
  lang: "zh" | "en" | "ja" | "fr";
};

type MemoryRecord = {
  id: string;
  session_id: string;
  created_at: string;
  source: string;
  source_hash: string;
  summary: string;
  keywords: string[];
  message_count: number;
  payload: Record<string, any>;
  domain: "episodic" | "semantic" | "preference";
  confidence: number;
  citations?: string[] | null;
  expires_at?: string | null;
  privacy_level: string;
  category: string;
};

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

// UI localization strings specifically for Memory Manager
const UI_TEXT = {
  zh: {
    title: "長期記憶體控制台",
    desc: "查看、搜索和分層整理 LAS 的偏好、知識與歷史會話總結。",
    searchPlaceholder: "搜尋關鍵字、標籤...",
    domainFilterAll: "所有領域",
    domainEpisodic: "會話歷史 (Episodic)",
    domainSemantic: "事實知識 (Semantic)",
    domainPreference: "使用者偏好 (Preference)",
    categoryTreeTitle: "分類資料夾",
    allCategories: "所有分類",
    noRecords: "沒有找到相關記憶。",
    addMemoryBtn: "+ 新增記憶",
    batchActions: "批次操作",
    batchDelete: "批次刪除",
    batchMove: "批次移動",
    pruneBtn: "清理過期記憶",
    confidence: "可信度",
    citations: "引用來源",
    expiresAt: "過期時間",
    sessionId: "會話 ID",
    createdAt: "創建時間",
    key: "鍵值 (Key)",
    summary: "記憶內容 / 總結",
    domain: "記憶類型",
    categoryPath: "分類路徑 (例如: user/preferences)",
    addModalTitle: "新增長期記憶",
    editModalTitle: "編輯記憶詳情",
    deleteConfirmTitle: "刪除記憶",
    deleteConfirmText: "確定要永久刪除這條記憶嗎？",
    batchMoveTitle: "批次移動分類",
    newCategoryLabel: "新分類路徑",
    recordsSelected: "已選取 {count} 項",
    successAlert: "操作成功",
    errorAlert: "操作失敗",
  },
  en: {
    title: "Long-Term Memory Console",
    desc: "View, search, and hierarchically organize user preferences, semantic knowledge, and episodic summaries.",
    searchPlaceholder: "Search keywords, tags...",
    domainFilterAll: "All Domains",
    domainEpisodic: "Session Summaries (Episodic)",
    domainSemantic: "Facts & Knowledge (Semantic)",
    domainPreference: "User Preferences (Preference)",
    categoryTreeTitle: "Category Folders",
    allCategories: "All Folders",
    noRecords: "No memory records found.",
    addMemoryBtn: "+ Add Memory",
    batchActions: "Batch Actions",
    batchDelete: "Batch Delete",
    batchMove: "Batch Move",
    pruneBtn: "Prune Expired",
    confidence: "Confidence",
    citations: "Citations",
    expiresAt: "Expires At",
    sessionId: "Session ID",
    createdAt: "Created At",
    key: "Key",
    summary: "Memory Content",
    domain: "Memory Domain",
    categoryPath: "Category Path (e.g. user/preferences)",
    addModalTitle: "Add Long-Term Memory",
    editModalTitle: "Edit Memory Details",
    deleteConfirmTitle: "Delete Memory",
    deleteConfirmText: "Are you sure you want to permanently delete this memory record?",
    batchMoveTitle: "Batch Move Category",
    newCategoryLabel: "New Category Path",
    recordsSelected: "{count} selected",
    successAlert: "Operation completed successfully",
    errorAlert: "Operation failed",
  },
};

export function LongTermMemoryView({ t, lang }: LongTermMemoryViewProps) {
  const ui = UI_TEXT[lang === "zh" ? "zh" : "en"];

  // Data States
  const [records, setRecords] = useState<MemoryRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Filter States
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedDomain, setSelectedDomain] = useState<string>("all");
  const [selectedCategoryPath, setSelectedCategoryPath] = useState<string>("all");
  const [expandedFolders, setExpandedFolders] = useState<Record<string, boolean>>({});

  // Selection States
  const [selectedKeys, setSelectedKeys] = useState<Record<string, { session_id: string; key: string }>>({});

  // Modal States
  const [addEditModalOpen, setAddEditModalOpen] = useState(false);
  const [editRecord, setEditRecord] = useState<MemoryRecord | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<MemoryRecord | null>(null);
  const [batchMoveOpen, setBatchMoveOpen] = useState(false);

  // Form Fields
  const [formSessionId, setFormSessionId] = useState("default-session");
  const [formKey, setFormKey] = useState("");
  const [formDomain, setFormDomain] = useState<"semantic" | "preference">("semantic");
  const [formCategory, setFormCategory] = useState("general");
  const [formSummary, setFormSummary] = useState("");
  const [formConfidence, setFormConfidence] = useState(1.0);
  const [formExpiresAt, setFormExpiresAt] = useState("");
  const [formCitations, setFormCitations] = useState("");
  const [newBatchCategory, setNewBatchCategory] = useState("");

  const host = API_BASE_URL;

  // Fetch memory records
  async function fetchRecords() {
    setLoading(true);
    try {
      const resp = await fetch(`${host}/v1/memory`);
      if (!resp.ok) throw new Error("Failed to fetch memory records");
      const data = await resp.json();
      setRecords(data.records || []);
      setError(null);
    } catch (err: any) {
      setError(err.message || "Unknown error occurred");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    fetchRecords();
  }, []);

  // Helpers to get all categories and count records inside
  const categoriesList = Array.from(new Set(records.map(r => r.category || "general")));

  // Build a tree of category nodes
  type CategoryTreeNode = {
    name: string;
    path: string;
    children: Record<string, CategoryTreeNode>;
    count: number;
  };

  function buildCategoryTree(paths: string[]): CategoryTreeNode {
    const root: CategoryTreeNode = { name: "Root", path: "", children: {}, count: 0 };

    paths.forEach(p => {
      const cleanPath = p.replace(/^\/|\/$/g, "");
      const parts = cleanPath ? cleanPath.split("/") : ["general"];

      let current = root;
      let currentPath = "";

      parts.forEach((part) => {
        currentPath = currentPath ? `${currentPath}/${part}` : part;
        if (!current.children[part]) {
          current.children[part] = {
            name: part,
            path: currentPath,
            children: {},
            count: 0,
          };
        }
        current = current.children[part];

        // Count records matching this category prefix or exact path
        current.count = records.filter(r => {
          const rPath = (r.category || "general").replace(/^\/|\/$/g, "");
          return rPath === currentPath || rPath.startsWith(currentPath + "/");
        }).length;
      });
    });

    return root;
  }

  const categoryTree = buildCategoryTree(categoriesList);

  // Form Submit Handler
  async function handleAddEditSubmit() {
    if (!formSummary.trim() || !formCategory.trim()) return;

    try {
      const citationsArray = formCitations
        .split(",")
        .map(c => c.trim())
        .filter(c => c.length > 0);

      if (editRecord) {
        // Edit record
        const payload = {
          session_id: editRecord.session_id,
          key: editRecord.id,
          summary: formSummary,
          domain: formDomain,
          category: formCategory,
          confidence: formConfidence,
          expires_at: formExpiresAt || null,
          citations: citationsArray.length > 0 ? citationsArray : null,
        };
        const resp = await fetch(`${host}/v1/memory/update`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        });
        if (!resp.ok) throw new Error("Failed to update record");
      } else {
        // Create new record (either preference or semantic)
        let endpoint = `${host}/v1/memory/preference`;
        let payload: any = {
          session: formSessionId,
          preference: formSummary,
          confidence: formConfidence,
          expires_at: formExpiresAt || null,
          category: formCategory,
        };

        const createResp = await fetch(endpoint, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        });
        if (!createResp.ok) throw new Error("Failed to create record");
        const createData = await createResp.json();

        if (formDomain === "semantic") {
          // Update its domain to semantic
          const updatePayload = {
            session_id: formSessionId,
            key: createData.record.id,
            summary: formSummary,
            domain: "semantic",
            category: formCategory,
            confidence: formConfidence,
            expires_at: formExpiresAt || null,
            citations: citationsArray.length > 0 ? citationsArray : null,
          };
          await fetch(`${host}/v1/memory/update`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(updatePayload),
          });
        }
      }

      setAddEditModalOpen(false);
      fetchRecords();
    } catch (err: any) {
      alert(`${ui.errorAlert}: ${err.message}`);
    }
  }

  // Delete Handler
  async function handleDeleteConfirm() {
    if (!deleteTarget) return;

    try {
      const resp = await fetch(`${host}/v1/memory/${deleteTarget.session_id}/${deleteTarget.id}`, {
        method: "DELETE",
      });
      if (!resp.ok) throw new Error("Failed to delete record");
      setDeleteTarget(null);
      fetchRecords();
    } catch (err: any) {
      alert(`${ui.errorAlert}: ${err.message}`);
    }
  }

  // Batch Delete Handler
  async function handleBatchDelete() {
    const keysArray = Object.values(selectedKeys);
    if (keysArray.length === 0) return;

    if (!confirm(lang === "zh" ? "確定要刪除所有已選取的記憶嗎？" : "Are you sure you want to delete all selected records?")) {
      return;
    }

    try {
      for (const item of keysArray) {
        await fetch(`${host}/v1/memory/${item.session_id}/${item.key}`, {
          method: "DELETE",
        });
      }
      setSelectedKeys({});
      fetchRecords();
    } catch (err: any) {
      alert(`${ui.errorAlert}: ${err.message}`);
    }
  }

  // Batch Move Handler
  async function handleBatchMoveSubmit() {
    const keysArray = Object.values(selectedKeys);
    if (keysArray.length === 0 || !newBatchCategory.trim()) return;

    try {
      const payload = {
        items: keysArray,
        new_category: newBatchCategory.trim(),
      };
      const resp = await fetch(`${host}/v1/memory/batch-move`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      if (!resp.ok) throw new Error("Failed to batch move records");

      setSelectedKeys({});
      setBatchMoveOpen(false);
      setNewBatchCategory("");
      fetchRecords();
    } catch (err: any) {
      alert(`${ui.errorAlert}: ${err.message}`);
    }
  }

  // Prune Handler
  async function handlePrune() {
    try {
      const resp = await fetch(`${host}/v1/memory/prune`, {
        method: "POST",
      });
      if (!resp.ok) throw new Error("Pruning failed");
      const data = await resp.json();
      alert(lang === "zh" ? `清理完成，共刪除 ${data.deleted_count} 條過期記憶。` : `Pruning done. Deleted ${data.deleted_count} expired records.`);
      fetchRecords();
    } catch (err: any) {
      alert(`${ui.errorAlert}: ${err.message}`);
    }
  }

  // Filter records locally
  const filteredRecords = records.filter(r => {
    // 1. Search Query Filter
    if (searchQuery.trim()) {
      const query = searchQuery.toLowerCase();
      const textToSearch = [
        r.id,
        r.summary,
        r.category,
        r.domain,
        ...(r.keywords || []),
      ].join(" ").toLowerCase();

      if (!textToSearch.includes(query)) return false;
    }

    // 2. Domain Filter
    if (selectedDomain !== "all" && r.domain !== selectedDomain) {
      return false;
    }

    // 3. Category Tree Filter
    if (selectedCategoryPath !== "all") {
      const cleanFilterPath = selectedCategoryPath.replace(/^\/|\/$/g, "");
      const cleanRecordPath = (r.category || "general").replace(/^\/|\/$/g, "");
      if (cleanRecordPath !== cleanFilterPath && !cleanRecordPath.startsWith(cleanFilterPath + "/")) {
        return false;
      }
    }

    return true;
  });

  // Toggle selection on a card
  function toggleSelection(rec: MemoryRecord) {
    const key = `${rec.session_id}:${rec.id}`;
    setSelectedKeys(prev => {
      const next = { ...prev };
      if (next[key]) {
        delete next[key];
      } else {
        next[key] = { session_id: rec.session_id, key: rec.id };
      }
      return next;
    });
  }

  const selectedCount = Object.keys(selectedKeys).length;

  // Render Category tree recursively
  function renderCategoryNode(node: CategoryTreeNode, depth: number = 0) {
    const isExpanded = !!expandedFolders[node.path];
    const hasChildren = Object.keys(node.children).length > 0;
    const isSelected = selectedCategoryPath === node.path;

    return (
      <div key={node.path || "root-folder"} className="select-none">
        {node.path && (
          <div
            className={`group flex items-center justify-between rounded-lg px-2.5 py-1.5 text-xs font-medium transition-all hover:bg-white/5 cursor-pointer ${
              isSelected ? "bg-white/10 text-white font-semibold" : "text-neutral-400 hover:text-neutral-200"
            }`}
            style={{ paddingLeft: `${Math.max(10, depth * 14)}px` }}
            onClick={() => setSelectedCategoryPath(node.path)}
          >
            <div className="flex items-center gap-1.5 min-w-0">
              <span
                className={`text-[10px] w-3 h-3 flex items-center justify-center font-mono opacity-60 hover:opacity-100 ${hasChildren ? "cursor-pointer" : "opacity-0"}`}
                onClick={(e) => {
                  e.stopPropagation();
                  setExpandedFolders(prev => ({ ...prev, [node.path]: !prev[node.path] }));
                }}
              >
                {hasChildren ? (isExpanded ? "▼" : "▶") : ""}
              </span>
              <span className="text-[12px] opacity-75">📁</span>
              <span className="truncate">{node.name}</span>
            </div>
            <span className="text-[9px] px-1.5 py-0.5 rounded bg-white/5 text-neutral-500 font-mono">
              {node.count}
            </span>
          </div>
        )}

        {(isExpanded || !node.path) && hasChildren && (
          <div className="space-y-0.5 mt-0.5">
            {Object.values(node.children)
              .sort((a, b) => a.name.localeCompare(b.name))
              .map(child => renderCategoryNode(child, depth + 1))}
          </div>
        )}
      </div>
    );
  }

  // Open modal for editing record
  function openEditModal(rec: MemoryRecord) {
    setEditRecord(rec);
    setFormSessionId(rec.session_id);
    setFormKey(rec.id);
    setFormDomain(rec.domain as any);
    setFormCategory(rec.category || "general");
    setFormSummary(rec.summary || "");
    setFormConfidence(rec.confidence || 1.0);
    setFormExpiresAt(rec.expires_at || "");
    setFormCitations(rec.citations ? rec.citations.join(", ") : "");
    setAddEditModalOpen(true);
  }

  // Open modal for adding record
  function openAddModal(folderPath: string = "general") {
    setEditRecord(null);
    setFormSessionId("default-session");
    setFormKey("");
    setFormDomain("semantic");
    setFormCategory(folderPath);
    setFormSummary("");
    setFormConfidence(1.0);
    setFormExpiresAt("");
    setFormCitations("");
    setAddEditModalOpen(true);
  }

  const episodicTotal = records.filter(r => r.domain === "episodic").length;
  const semanticTotal = records.filter(r => r.domain === "semantic").length;
  const preferenceTotal = records.filter(r => r.domain === "preference").length;

  return (
    <Surface elevated className="flex h-full flex-col overflow-hidden p-6">
      {/* Header */}
      <div className="mb-5 flex flex-shrink-0 flex-col gap-4 md:flex-row md:items-end md:justify-between">
        <div>
          <p className="text-[10px] font-bold uppercase tracking-[0.18em] t3">BRAIN LAYER</p>
          <h2 className="mt-1 text-xl font-bold t1">{ui.title}</h2>
          <p className="mt-1 max-w-2xl text-xs leading-relaxed t3">{ui.desc}</p>
        </div>
        <div className="flex items-center gap-3">
          <Button type="button" variant="quiet" onClick={handlePrune} className="border border-neutral-700">
            🧹 {ui.pruneBtn}
          </Button>
          <Button type="button" variant="primary" onClick={() => openAddModal("general")}>
            {ui.addMemoryBtn}
          </Button>
        </div>
      </div>

      {/* Tiles */}
      <div className="mb-5 grid grid-cols-2 gap-3 sm:grid-cols-4 flex-shrink-0">
        <MetricTile label="Total Records" value={records.length} />
        <MetricTile label="Episodic Logs" value={episodicTotal} tone="success" />
        <MetricTile label="Semantic Facts" value={semanticTotal} tone="accent" />
        <MetricTile label="Preferences" value={preferenceTotal} tone="warning" />
      </div>

      {/* Main Split Layout */}
      <div className="flex min-h-0 flex-1 gap-5 overflow-hidden">
        {/* Left Column: Folders */}
        <div className="w-64 border-r border-neutral-800/80 pr-4 flex flex-col flex-shrink-0 min-h-0 overflow-y-auto">
          <h3 className="text-[10px] font-bold uppercase tracking-[0.12em] text-neutral-500 mb-3 px-2">
            {ui.categoryTreeTitle}
          </h3>
          <div className="space-y-1.5 flex-1 min-h-0 overflow-y-auto">
            {/* All Categories Button */}
            <div
              className={`flex items-center justify-between rounded-lg px-2.5 py-1.5 text-xs font-semibold cursor-pointer ${
                selectedCategoryPath === "all" ? "bg-white/10 text-white" : "text-neutral-400 hover:bg-white/5"
              }`}
              onClick={() => setSelectedCategoryPath("all")}
            >
              <div className="flex items-center gap-1.5">
                <span>📁</span>
                <span>{ui.allCategories}</span>
              </div>
              <span className="text-[9px] px-1.5 py-0.5 rounded bg-white/5 text-neutral-500 font-mono">
                {records.length}
              </span>
            </div>

            {/* Tree root */}
            {categoryTree && renderCategoryNode(categoryTree, 0)}
          </div>
        </div>

        {/* Right Column: Records list */}
        <div className="flex-1 flex flex-col min-h-0">
          {/* Filters Area */}
          <div className="mb-4 flex flex-shrink-0 flex-col gap-3 sm:flex-row sm:items-center">
            {/* Search Input */}
            <div className="relative flex-1">
              <input
                type="text"
                value={searchQuery}
                onChange={e => setSearchQuery(e.target.value)}
                placeholder={ui.searchPlaceholder}
                className="field-input w-full pl-8 pr-3 py-1.5 text-xs rounded-lg"
              />
              <span className="absolute left-2.5 top-2 text-[10px] opacity-40">🔍</span>
            </div>

            {/* Domain Dropdown */}
            <select
              value={selectedDomain}
              onChange={e => setSelectedDomain(e.target.value)}
              className="field-input text-xs py-1.5 px-3 rounded-lg"
            >
              <option value="all">{ui.domainFilterAll}</option>
              <option value="episodic">{ui.domainEpisodic}</option>
              <option value="semantic">{ui.domainSemantic}</option>
              <option value="preference">{ui.domainPreference}</option>
            </select>
          </div>

          {/* Batch Actions Bar */}
          {selectedCount > 0 && (
            <div className="mb-4 flex items-center justify-between rounded-lg bg-neutral-900 border border-neutral-800 p-3 flex-shrink-0">
              <span className="text-xs text-neutral-300 font-medium">
                {ui.recordsSelected.replace("{count}", String(selectedCount))}
              </span>
              <div className="flex items-center gap-2">
                <Button type="button" variant="quiet" onClick={() => setBatchMoveOpen(true)} className="border border-neutral-700">
                  📁 {ui.batchMove}
                </Button>
                <Button type="button" variant="danger" onClick={handleBatchDelete}>
                  🗑️ {ui.batchDelete}
                </Button>
              </div>
            </div>
          )}

          {/* Records Grid */}
          <div className="flex-1 overflow-y-auto min-h-0 pr-1">
            {loading ? (
              <div className="flex h-48 items-center justify-center text-xs text-neutral-500">
                Loading memory records...
              </div>
            ) : error ? (
              <div className="flex h-48 items-center justify-center text-xs text-red-400">
                Error: {error}
              </div>
            ) : filteredRecords.length === 0 ? (
              <div className="flex h-48 flex-col items-center justify-center text-center">
                <p className="text-xs text-neutral-500">{ui.noRecords}</p>
              </div>
            ) : (
              <div className="grid grid-cols-1 gap-4 pb-4">
                {filteredRecords.map(rec => {
                  const keyString = `${rec.session_id}:${rec.id}`;
                  const isChecked = !!selectedKeys[keyString];
                  let badgeTone: "success" | "accent" | "warning" = "success";
                  if (rec.domain === "semantic") badgeTone = "accent";
                  if (rec.domain === "preference") badgeTone = "warning";

                  return (
                    <Surface key={keyString} className="flex gap-4 p-4 border border-neutral-800/80 hover:border-neutral-700/80 transition-all">
                      {/* Checkbox */}
                      <div className="pt-0.5 flex-shrink-0">
                        <input
                          type="checkbox"
                          checked={isChecked}
                          onChange={() => toggleSelection(rec)}
                          className="rounded border-neutral-800 bg-neutral-900 text-neutral-400 focus:ring-0 focus:ring-offset-0 h-4 w-4 cursor-pointer"
                        />
                      </div>

                      {/* Main card */}
                      <div className="min-w-0 flex-1">
                        <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
                          <div className="flex items-center gap-2">
                            <StatusBadge tone={badgeTone}>{rec.domain.toUpperCase()}</StatusBadge>
                            <span className="text-[10px] font-mono text-neutral-500">
                              {rec.id}
                            </span>
                            <span className="text-[10px] px-1.5 py-0.5 rounded bg-neutral-800 font-mono text-neutral-400">
                              Folder: {rec.category || "general"}
                            </span>
                          </div>
                          <div className="flex items-center gap-2">
                            <span className="text-[10px] text-neutral-500 font-mono">
                              {ui.confidence}: <b className="text-white">{(rec.confidence ?? 1.0).toFixed(1)}</b>
                            </span>
                          </div>
                        </div>

                        {/* Content Summary */}
                        <p className="text-xs leading-relaxed text-neutral-200 font-medium whitespace-pre-wrap">
                          {rec.summary}
                        </p>

                        {/* Citations */}
                        {rec.citations && rec.citations.length > 0 && (
                          <div className="mt-3 flex items-start gap-1.5 flex-wrap">
                            <span className="text-[10px] text-neutral-500 font-bold uppercase tracking-[0.08em]">{ui.citations}:</span>
                            {rec.citations.map((c, i) => (
                              <span key={i} className="text-[9px] px-1.5 py-0.5 rounded bg-neutral-800/60 font-mono text-neutral-400 border border-neutral-800">
                                {c}
                              </span>
                            ))}
                          </div>
                        )}

                        {/* Footer details */}
                        <div className="mt-3 flex flex-wrap items-center gap-x-4 gap-y-1 text-[9px] text-neutral-600 font-mono">
                          <span>{ui.sessionId}: {rec.session_id}</span>
                          <span>{ui.createdAt}: {rec.created_at ? rec.created_at.slice(0, 19).replace("T", " ") : "--"}</span>
                          {rec.expires_at && <span className="text-red-400">{ui.expiresAt}: {rec.expires_at}</span>}
                        </div>
                      </div>

                      {/* Actions */}
                      <div className="flex flex-col gap-2 justify-start flex-shrink-0">
                        {rec.domain !== "episodic" && (
                          <Button type="button" variant="quiet" onClick={() => openEditModal(rec)} className="px-2 py-1 text-[10px] hover:text-white">
                            ✏️
                          </Button>
                        )}
                        <Button type="button" variant="quiet" onClick={() => setDeleteTarget(rec)} className="px-2 py-1 text-[10px] hover:text-red-400">
                          🗑️
                        </Button>
                      </div>
                    </Surface>
                  );
                })}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* CRUD Add/Edit Modal */}
      {addEditModalOpen && (
        <Modal
          title={editRecord ? ui.editModalTitle : ui.addModalTitle}
          onConfirm={handleAddEditSubmit}
          onCancel={() => setAddEditModalOpen(false)}
          confirmText={t.confirm}
          cancelText={t.cancel}
        >
          <div className="space-y-4 max-h-[480px] overflow-y-auto pr-1">
            {!editRecord && (
              <div>
                <label className="block text-[10px] font-bold uppercase text-neutral-400 mb-1.5">{ui.sessionId}</label>
                <input
                  type="text"
                  value={formSessionId}
                  onChange={e => setFormSessionId(e.target.value)}
                  className="field-input w-full rounded-lg p-2 text-xs"
                />
              </div>
            )}
            {editRecord && (
              <div>
                <label className="block text-[10px] font-bold uppercase text-neutral-400 mb-1.5">{ui.key}</label>
                <input
                  type="text"
                  value={formKey}
                  disabled
                  className="field-input w-full rounded-lg p-2 text-xs opacity-60 font-mono"
                />
              </div>
            )}
            <div>
              <label className="block text-[10px] font-bold uppercase text-neutral-400 mb-1.5">{ui.domain}</label>
              <select
                value={formDomain}
                onChange={e => setFormDomain(e.target.value as any)}
                disabled={editRecord?.domain === "episodic"}
                className="field-input w-full rounded-lg p-2 text-xs"
              >
                <option value="semantic">{ui.domainSemantic}</option>
                <option value="preference">{ui.domainPreference}</option>
              </select>
            </div>
            <div>
              <label className="block text-[10px] font-bold uppercase text-neutral-400 mb-1.5">{ui.categoryPath}</label>
              <input
                type="text"
                value={formCategory}
                onChange={e => setFormCategory(e.target.value)}
                placeholder="e.g. user/preferences/coding"
                className="field-input w-full rounded-lg p-2 text-xs"
              />
            </div>
            <div>
              <label className="block text-[10px] font-bold uppercase text-neutral-400 mb-1.5">{ui.summary}</label>
              <textarea
                value={formSummary}
                onChange={e => setFormSummary(e.target.value)}
                rows={4}
                className="field-input w-full rounded-lg p-2.5 text-xs font-medium resize-none"
              />
            </div>
            <div>
              <label className="block text-[10px] font-bold uppercase text-neutral-400 mb-1.5">
                {ui.confidence}: <span className="text-white font-mono">{formConfidence.toFixed(1)}</span>
              </label>
              <input
                type="range"
                min="0.1"
                max="1.0"
                step="0.1"
                value={formConfidence}
                onChange={e => setFormConfidence(parseFloat(e.target.value))}
                className="w-full cursor-pointer accent-sky-400 h-1.5 bg-neutral-800 rounded-lg appearance-none"
              />
            </div>
            {formDomain === "semantic" && (
              <div>
                <label className="block text-[10px] font-bold uppercase text-neutral-400 mb-1.5">{ui.citations} (comma separated)</label>
                <input
                  type="text"
                  value={formCitations}
                  onChange={e => setFormCitations(e.target.value)}
                  placeholder="e.g. adr-001, doc-api"
                  className="field-input w-full rounded-lg p-2 text-xs"
                />
              </div>
            )}
            <div>
              <label className="block text-[10px] font-bold uppercase text-neutral-400 mb-1.5">{ui.expiresAt} (YYYY-MM-DD, optional)</label>
              <input
                type="text"
                value={formExpiresAt}
                onChange={e => setFormExpiresAt(e.target.value)}
                placeholder="e.g. 2026-12-31"
                className="field-input w-full rounded-lg p-2 text-xs font-mono"
              />
            </div>
          </div>
        </Modal>
      )}

      {/* Delete Confirmation Modal */}
      {deleteTarget && (
        <Modal
          title={ui.deleteConfirmTitle}
          onConfirm={handleDeleteConfirm}
          onCancel={() => setDeleteTarget(null)}
          confirmText={t.confirm}
          cancelText={t.cancel}
          danger
        >
          <p className="text-xs text-neutral-300 leading-relaxed mb-3">
            {ui.deleteConfirmText}
          </p>
          <Surface className="p-3 border border-neutral-800 text-xs font-medium text-neutral-400 whitespace-pre-wrap">
            {deleteTarget.summary}
          </Surface>
        </Modal>
      )}

      {/* Batch Move Modal */}
      {batchMoveOpen && (
        <Modal
          title={ui.batchMoveTitle}
          onConfirm={handleBatchMoveSubmit}
          onCancel={() => setBatchMoveOpen(false)}
          confirmText={t.confirm}
          cancelText={t.cancel}
        >
          <div className="space-y-3">
            <label className="block text-[10px] font-bold uppercase text-neutral-400">{ui.newCategoryLabel}</label>
            <input
              type="text"
              value={newBatchCategory}
              onChange={e => setNewBatchCategory(e.target.value)}
              placeholder="e.g. user/preferences/hobbies"
              className="field-input w-full rounded-lg p-2 text-xs"
              autoFocus
            />
          </div>
        </Modal>
      )}
    </Surface>
  );
}
