import { useEffect, useState, useRef, useCallback } from "react";
import { agentApi } from "../api/agentApi";
import type { AgentSummary, DriveAgentState, SpocPoolEntry, KBEntry } from "../api/agentApi";
import { Button } from "../../../shared/components/Button";
import { StatusBadge, statusToneFromDriveStatus } from "../../../shared/components/StatusBadge";
import { LoadingBlock } from "../../../shared/components/LoadingBlock";
import { useToast } from "../../../shared/components/ToastProvider";

// ── Constants ─────────────────────────────────────────────────────────
const STATUS_PIPELINE: Record<string, { icon: string; label: string; color: string }> = {
  INIT:           { icon: "🆕", label: "Created",          color: "#6366f1" },
  CONTACTED:      { icon: "📧", label: "Email Sent",        color: "#f59e0b" },
  INFO_SHARED:    { icon: "📄", label: "JD Received",       color: "#8b5cf6" },
  DRIVE_CONFIRMED:{ icon: "✅", label: "Drive Confirmed",   color: "#10b981" },
  SPOC_ASSIGNED:  { icon: "👤", label: "SPOC Assigned",     color: "#06b6d4" },
  SPOC_HANDLING:  { icon: "💬", label: "In Progress",       color: "#22c55e" },
  COMPLETED:      { icon: "🏁", label: "Completed",         color: "#6b7280" },
  DONE:           { icon: "✔️", label: "Done",              color: "#6b7280" },
};

const PIPELINE_STEPS = ["INIT","CONTACTED","INFO_SHARED","DRIVE_CONFIRMED","SPOC_ASSIGNED","SPOC_HANDLING","COMPLETED"];

interface LogEntry {
  id: number;
  ts: string;
  type: "info" | "action" | "success" | "error";
  actor: string;
  msg: string;
}
let logId = 0;

type Tab = "pipeline" | "spocs";

// ── Component ─────────────────────────────────────────────────────────
export function AgentConsolePage() {
  const { pushToast } = useToast();
  const [tab, setTab] = useState<Tab>("pipeline");
  const [summary, setSummary] = useState<AgentSummary | null>(null);
  const [spocs, setSpocs] = useState<SpocPoolEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [running, setRunning] = useState<string | null>(null);
  const [expanded, setExpanded] = useState<number | null>(null);
  const [spocForm, setSpocForm] = useState({ name: "", email: "" });
  const [spocLoading, setSpocLoading] = useState(false);
  const [kbData, setKbData] = useState<Record<number, KBEntry[]>>({});
  const [kbLoading, setKbLoading] = useState<number | null>(null);
  const logEnd = useRef<HTMLDivElement>(null);

  const addLog = useCallback((type: LogEntry["type"], actor: string, msg: string) => {
    setLogs(p => [...p, { id: ++logId, ts: new Date().toLocaleTimeString(), type, actor, msg }]);
  }, []);

  const loadStatus = useCallback(async () => {
    try {
      const data = await agentApi.getStatus();
      setSummary(data);
    } catch (e) {
      addLog("error", "SYSTEM", `Status fetch failed: ${e instanceof Error ? e.message : e}`);
    } finally { setLoading(false); }
  }, [addLog]);

  const loadSpocs = useCallback(async () => {
    try { setSpocs(await agentApi.listSpocs()); } catch {}
  }, []);

  useEffect(() => { void loadStatus(); void loadSpocs(); }, []);
  useEffect(() => { const t = setInterval(() => void loadStatus(), 15000); return () => clearInterval(t); }, [loadStatus]);
  useEffect(() => { logEnd.current?.scrollIntoView({ behavior: "smooth" }); }, [logs]);

  async function runAction(driveId: number, action: string, company: string) {
    const key = `${driveId}-${action}`;
    setRunning(key);
    addLog("action", "AGENT", `Executing ${action} for ${company}…`);
    try {
      const r = await agentApi.runStep(driveId, action);
      addLog(r.success ? "success" : "error", "AGENT", r.message);
      pushToast(r.message, r.success ? undefined : "error");
    } catch (e) { addLog("error", "AGENT", String(e)); }
    finally { setRunning(null); await loadStatus(); }
  }

  async function loadKb(companyId: number) {
    setKbLoading(companyId);
    try {
      const data = await agentApi.getKnowledgeBase(companyId);
      setKbData(prev => ({ ...prev, [companyId]: data }));
    } catch (e) {
      pushToast("Failed to load Knowledge Base", "error");
    } finally {
      setKbLoading(null);
    }
  }

  async function addSpoc() {
    if (!spocForm.name || !spocForm.email) return;
    setSpocLoading(true);
    try {
      await agentApi.addSpoc(spocForm.name, spocForm.email);
      setSpocForm({ name: "", email: "" });
      pushToast(`SPOC ${spocForm.name} added!`);
      await loadSpocs();
    } catch (e) { pushToast("Failed to add SPOC", "error"); }
    finally { setSpocLoading(false); }
  }

  async function removeSpoc(id: number) {
    await agentApi.removeSpoc(id);
    await loadSpocs();
    pushToast("SPOC removed");
  }

  async function toggleSpoc(id: number) {
    await agentApi.toggleSpoc(id);
    await loadSpocs();
  }

  if (loading) return <LoadingBlock label="Loading Agent Console…" />;

  const logColors: Record<LogEntry["type"], string> = {
    info: "var(--text-muted)", action: "#f59e0b", success: "#22c55e", error: "#ef4444"
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16, height: "calc(100vh - 100px)" }}>

      {/* ── Top Summary Bar ── */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(5, 1fr)", gap: 10 }}>
        {[
          { label: "Total Drives",    value: summary?.total_drives ?? 0,       icon: "📋", color: "#6366f1" },
          { label: "Active",          value: summary?.active_drives ?? 0,      icon: "🔄", color: "#f59e0b" },
          { label: "Pending Actions", value: summary?.pending_actions ?? 0,    icon: "⏳", color: "#ef4444" },
          { label: "Awaiting HR",     value: summary?.questions_awaiting_hr ?? 0, icon: "📨", color: "#10b981" },
          { label: "SPOC Pool",       value: spocs.filter(s => s.is_available).length, icon: "👥", color: "#06b6d4" },
        ].map(s => (
          <div key={s.label} style={{
            background: "var(--bg-surface)", border: "1px solid var(--border)",
            borderRadius: "var(--radius-sm)", padding: "12px 14px",
            display: "flex", alignItems: "center", gap: 10,
            borderTop: `3px solid ${s.color}`,
          }}>
            <span style={{ fontSize: 22 }}>{s.icon}</span>
            <div>
              <div style={{ fontSize: 20, fontWeight: 700, color: "var(--text-primary)" }}>{s.value}</div>
              <div style={{ fontSize: 11, color: "var(--text-muted)" }}>{s.label}</div>
            </div>
          </div>
        ))}
      </div>

      {/* ── Tabs ── */}
      <div style={{ display: "flex", gap: 4, borderBottom: "1px solid var(--border)", paddingBottom: 0 }}>
        {(["pipeline", "spocs"] as Tab[]).map(t => (
          <button key={t} onClick={() => setTab(t)} style={{
            background: "none", border: "none", cursor: "pointer",
            padding: "8px 18px", fontWeight: 600, fontSize: 13,
            color: tab === t ? "var(--text-accent)" : "var(--text-muted)",
            borderBottom: tab === t ? "2px solid var(--text-accent)" : "2px solid transparent",
            transition: "all 0.15s",
          }}>
            {t === "pipeline" ? "🤖 Drive Pipeline" : "👥 SPOC Pool"}
          </button>
        ))}
        <div style={{ flex: 1 }} />
        <Button variant="secondary" size="sm" onClick={() => { void loadStatus(); void loadSpocs(); }}>
          ↻ Refresh
        </Button>
        <Button variant="ghost" size="sm" onClick={() => setLogs([])}>Clear Log</Button>
      </div>

      {/* ── Content Area ── */}
      <div style={{ flex: 1, display: "flex", gap: 16, minHeight: 0 }}>

        {tab === "pipeline" && (
          <>
            {/* Drive Cards */}
            <div style={{ width: 400, overflowY: "auto", display: "flex", flexDirection: "column", gap: 10 }}>
              {(!summary?.drives || summary.drives.length === 0) && (
                <div style={{ textAlign: "center", color: "var(--text-muted)", paddingTop: 40, fontSize: 13 }}>
                  <div style={{ fontSize: 32, marginBottom: 8 }}>🤖</div>
                  No active drives. Create a company drive to begin.
                </div>
              )}
              {summary?.drives.map(drive => {
                const isExp = expanded === drive.drive_id;
                const info = STATUS_PIPELINE[drive.status] ?? { icon: "❓", label: drive.status, color: "#6b7280" };
                const stepIdx = PIPELINE_STEPS.indexOf(drive.status);

                return (
                  <div key={drive.drive_id} style={{
                    background: "var(--bg-surface)", border: `1px solid ${isExp ? "var(--text-accent)" : "var(--border)"}`,
                    borderRadius: "var(--radius-sm)", overflow: "hidden",
                    transition: "border-color 0.15s",
                  }}>
                    {/* Card Header */}
                    <div onClick={() => setExpanded(isExp ? null : drive.drive_id)} style={{
                      padding: "12px 14px", cursor: "pointer", display: "flex",
                      alignItems: "center", justifyContent: "space-between",
                    }}>
                      <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                        <span style={{ fontSize: 20 }}>{info.icon}</span>
                        <div>
                          <div style={{ fontWeight: 700, fontSize: 13 }}>{drive.company_name}</div>
                          <div style={{ fontSize: 11, color: "var(--text-muted)" }}>{drive.hr_email}</div>
                        </div>
                      </div>
                      <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                        <StatusBadge tone={statusToneFromDriveStatus(drive.status)}>{drive.status}</StatusBadge>
                        <span style={{ color: "var(--text-muted)", fontSize: 12 }}>{isExp ? "▲" : "▼"}</span>
                      </div>
                    </div>

                    {/* Pipeline Progress Bar */}
                    <div style={{ padding: "0 14px 10px", display: "flex", gap: 3, alignItems: "center" }}>
                      {PIPELINE_STEPS.slice(0, -1).map((step, i) => (
                        <div key={step} style={{
                          flex: 1, height: 4, borderRadius: 99,
                          background: i <= stepIdx ? info.color : "var(--border)",
                          transition: "background 0.3s",
                        }} />
                      ))}
                    </div>

                    {/* Mini stats */}
                    <div style={{ display: "grid", gridTemplateColumns: "repeat(4,1fr)", gap: 6, padding: "0 14px 12px" }}>
                      {[
                        { v: drive.emails_sent, l: "Sent", color: "#6366f1" },
                        { v: drive.emails_received, l: "Recv'd", color: "#10b981" },
                        { v: drive.questions_total, l: "Questions", color: "#f59e0b" },
                        { v: drive.has_telegram_group ? "✓" : "—", l: "Telegram", color: drive.has_telegram_group ? "#22c55e" : "var(--text-muted)" },
                      ].map(s => (
                        <div key={s.l} style={{
                          background: "var(--bg-primary)", borderRadius: 6, padding: "6px 8px", textAlign: "center",
                        }}>
                          <div style={{ fontSize: 15, fontWeight: 700, color: s.color }}>{s.v}</div>
                          <div style={{ fontSize: 9, color: "var(--text-muted)" }}>{s.l}</div>
                        </div>
                      ))}
                    </div>

                    {/* Autonomous Agent Status */}
                    <div style={{ margin: "0 14px 10px", padding: "8px 10px", background: "rgba(99,102,241,0.07)", borderRadius: 6, fontSize: 11, color: "var(--text-muted)" }}>
                      <span style={{ color: "var(--text-accent)", fontWeight: 600, marginRight: 6 }}>🤖 AGENT</span>
                      Next: <strong style={{ color: "var(--text-primary)" }}>{drive.next_action}</strong>
                      {drive.spoc_name && <span style={{ marginLeft: 10 }}>· SPOC: <strong style={{ color: "var(--text-primary)" }}>{drive.spoc_name}</strong></span>}
                    </div>

                    {/* Question Badges */}
                    {drive.questions_total > 0 && (
                      <div style={{ display: "flex", gap: 5, flexWrap: "wrap", padding: "0 14px 10px" }}>
                        {[
                          { v: drive.questions_auto_answered, l: "auto", bg: "rgba(99,102,241,0.15)", c: "var(--text-accent)" },
                          { v: drive.questions_forwarded, l: "→HR", bg: "rgba(245,158,11,0.15)", c: "#f59e0b" },
                          { v: drive.questions_hr_answered, l: "answered", bg: "rgba(34,197,94,0.15)", c: "#22c55e" },
                          { v: drive.questions_pending, l: "pending", bg: "rgba(239,68,68,0.15)", c: "#ef4444" },
                        ].filter(b => b.v > 0).map(b => (
                          <span key={b.l} style={{ fontSize: 10, background: b.bg, color: b.c, borderRadius: 4, padding: "2px 7px" }}>
                            {b.v} {b.l}
                          </span>
                        ))}
                      </div>
                    )}

                    {/* Latest Activity */}
                    {drive.latest_activity && (
                      <div style={{ margin: "0 14px 10px", fontSize: 11, color: "var(--text-muted)", borderTop: "1px solid var(--border)", paddingTop: 8 }}>
                        {drive.latest_activity}
                      </div>
                    )}

                    {/* Expanded Actions */}
                    {isExp && (
                      <>
                        {/* Knowledge Base Viewer */}
                        {drive.company_id && (
                          <div style={{ padding: "0 14px 14px", borderTop: "1px solid var(--border)", paddingTop: 10 }}>
                            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 8 }}>
                              <div style={{ fontSize: 11, color: "var(--text-muted)", fontWeight: 600 }}>
                                📚 Extracted Knowledge Base:
                              </div>
                              {!kbData[drive.company_id] && (
                                <Button size="sm" variant="ghost" onClick={(e) => { e.stopPropagation(); loadKb(drive.company_id!); }}>
                                  {kbLoading === drive.company_id ? "Loading..." : "Load KB"}
                                </Button>
                              )}
                            </div>
                            
                            {kbData[drive.company_id] && kbData[drive.company_id].length === 0 && (
                              <div style={{ fontSize: 11, color: "var(--text-muted)", fontStyle: "italic" }}>
                                No facts extracted yet. Sync HR emails to build KB.
                              </div>
                            )}
                            
                            {kbData[drive.company_id] && kbData[drive.company_id].length > 0 && (
                              <div style={{ display: "flex", flexDirection: "column", gap: 6, maxHeight: 200, overflowY: "auto", background: "var(--bg-primary)", padding: 8, borderRadius: 6 }}>
                                {kbData[drive.company_id].map(entry => (
                                  <div key={entry.id} style={{ fontSize: 11 }}>
                                    <span style={{ color: "var(--text-accent)", fontWeight: 600 }}>[{entry.category}]</span>{" "}
                                    <strong style={{ color: "var(--text-primary)" }}>{entry.topic}:</strong>{" "}
                                    <span style={{ color: "var(--text-muted)" }}>{entry.content}</span>
                                  </div>
                                ))}
                              </div>
                            )}
                          </div>
                        )}

                        {/* Manual Actions */}
                        <div style={{ padding: "0 14px 14px", borderTop: "1px solid var(--border)", paddingTop: 10, display: "flex", flexWrap: "wrap", gap: 6 }}>
                          <div style={{ width: "100%", fontSize: 11, color: "var(--text-muted)", marginBottom: 6, fontWeight: 600 }}>
                            Manual Override Actions:
                          </div>
                          {[
                            { action: "SYNC_EMAILS", label: "📥 Sync Emails" },
                            { action: "SEND_EMAIL", label: "📧 Send Email" },
                            { action: "CREATE_TELEGRAM", label: "💬 Create Group" },
                            { action: "DRAFT_BROADCAST", label: "📢 Broadcast" },
                            { action: "CONFIRM_DRIVE", label: "✅ Confirm Drive" },
                          ].map(({ action, label }) => (
                            <Button key={action} size="sm" variant="secondary" disabled={!!running}
                              onClick={e => { e.stopPropagation(); void runAction(drive.drive_id, action, drive.company_name); }}>
                              {running === `${drive.drive_id}-${action}` ? "Running…" : label}
                            </Button>
                          ))}
                        </div>
                      </>
                    )}
                  </div>
                );
              })}
            </div>

            {/* Live Log Feed */}
            <div style={{ flex: 1, display: "flex", flexDirection: "column", minWidth: 0 }}>
              <div style={{ fontSize: 12, fontWeight: 600, color: "var(--text-muted)", marginBottom: 6 }}>
                🖥️ Agent Activity Log
                <span style={{ marginLeft: 10, background: "rgba(34,197,94,0.15)", color: "#22c55e", borderRadius: 99, padding: "2px 8px", fontSize: 10 }}>
                  ● LIVE
                </span>
              </div>
              <div style={{
                flex: 1, overflow: "auto", background: "var(--bg-surface)", border: "1px solid var(--border)",
                borderRadius: "var(--radius-sm)", padding: 14,
                fontFamily: "'JetBrains Mono','Fira Code',monospace", fontSize: 12,
              }}>
                {logs.length === 0 ? (
                  <div style={{ color: "var(--text-muted)", textAlign: "center", marginTop: 40 }}>
                    Agent logs appear here as actions execute…
                  </div>
                ) : logs.map(log => (
                  <div key={log.id} style={{ marginBottom: 6, lineHeight: 1.6 }}>
                    <span style={{ color: "var(--text-muted)", marginRight: 8 }}>{log.ts}</span>
                    <span style={{
                      background: log.actor === "AGENT" ? "rgba(99,102,241,0.15)" : "rgba(107,114,128,0.15)",
                      color: log.actor === "AGENT" ? "var(--text-accent)" : "var(--text-muted)",
                      borderRadius: 4, padding: "1px 6px", fontSize: 10, fontWeight: 700, marginRight: 8,
                    }}>{log.actor}</span>
                    <span style={{ color: logColors[log.type] }}>{log.msg}</span>
                  </div>
                ))}
                <div ref={logEnd} />
              </div>
            </div>
          </>
        )}

        {tab === "spocs" && (
          <div style={{ flex: 1, display: "flex", flexDirection: "column", gap: 16 }}>
            {/* Add SPOC Form */}
            <div style={{
              background: "var(--bg-surface)", border: "1px solid var(--border)",
              borderRadius: "var(--radius-sm)", padding: 16,
            }}>
              <div style={{ fontWeight: 700, fontSize: 14, marginBottom: 12 }}>➕ Add SPOC to Pool</div>
              <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
                <input
                  placeholder="Full Name"
                  value={spocForm.name}
                  onChange={e => setSpocForm(p => ({ ...p, name: e.target.value }))}
                  style={{
                    flex: 1, minWidth: 160, background: "var(--bg-primary)", border: "1px solid var(--border)",
                    borderRadius: "var(--radius-sm)", padding: "8px 12px", color: "var(--text-primary)",
                    fontSize: 13,
                  }}
                />
                <input
                  placeholder="Email Address"
                  type="email"
                  value={spocForm.email}
                  onChange={e => setSpocForm(p => ({ ...p, email: e.target.value }))}
                  style={{
                    flex: 2, minWidth: 200, background: "var(--bg-primary)", border: "1px solid var(--border)",
                    borderRadius: "var(--radius-sm)", padding: "8px 12px", color: "var(--text-primary)",
                    fontSize: 13,
                  }}
                />
                <Button onClick={addSpoc} disabled={spocLoading || !spocForm.name || !spocForm.email}>
                  {spocLoading ? "Adding…" : "Add SPOC"}
                </Button>
              </div>
              <div style={{ fontSize: 11, color: "var(--text-muted)", marginTop: 8 }}>
                The autonomous agent picks the least-loaded available SPOC when assigning to a new confirmed drive.
              </div>
            </div>

            {/* SPOC List */}
            <div style={{ flex: 1, overflowY: "auto" }}>
              <div style={{ fontWeight: 700, fontSize: 14, marginBottom: 10 }}>
                👥 SPOC Pool ({spocs.length} total · {spocs.filter(s => s.is_available).length} available)
              </div>
              {spocs.length === 0 ? (
                <div style={{
                  textAlign: "center", color: "var(--text-muted)", padding: 40,
                  background: "var(--bg-surface)", borderRadius: "var(--radius-sm)",
                  border: "1px solid var(--border)", fontSize: 13,
                }}>
                  <div style={{ fontSize: 32, marginBottom: 8 }}>👥</div>
                  No SPOCs added yet. Add one above to enable autonomous SPOC assignment.
                </div>
              ) : (
                <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                  {spocs.map(spoc => (
                    <div key={spoc.id} style={{
                      background: "var(--bg-surface)", border: "1px solid var(--border)",
                      borderRadius: "var(--radius-sm)", padding: "12px 16px",
                      display: "flex", alignItems: "center", justifyContent: "space-between",
                      opacity: spoc.is_available ? 1 : 0.55,
                    }}>
                      <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
                        <div style={{
                          width: 38, height: 38, borderRadius: "50%", fontSize: 14, fontWeight: 700,
                          background: "var(--accent-light)", color: "var(--text-accent)",
                          display: "flex", alignItems: "center", justifyContent: "center",
                        }}>
                          {spoc.name.charAt(0).toUpperCase()}
                        </div>
                        <div>
                          <div style={{ fontWeight: 600, fontSize: 13 }}>{spoc.name}</div>
                          <div style={{ fontSize: 11, color: "var(--text-muted)" }}>{spoc.email}</div>
                        </div>
                      </div>

                      <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
                        <div style={{ textAlign: "center" }}>
                          <div style={{ fontSize: 16, fontWeight: 700, color: spoc.active_drives > 0 ? "#f59e0b" : "var(--text-primary)" }}>
                            {spoc.active_drives}
                          </div>
                          <div style={{ fontSize: 10, color: "var(--text-muted)" }}>Active Drives</div>
                        </div>

                        <span style={{
                          fontSize: 11, fontWeight: 600, borderRadius: 99, padding: "3px 10px",
                          background: spoc.is_available ? "rgba(34,197,94,0.15)" : "rgba(239,68,68,0.12)",
                          color: spoc.is_available ? "#22c55e" : "#ef4444",
                        }}>
                          {spoc.is_available ? "● Available" : "○ Unavailable"}
                        </span>

                        <div style={{ display: "flex", gap: 6 }}>
                          <Button size="sm" variant="secondary" onClick={() => toggleSpoc(spoc.id)}>
                            {spoc.is_available ? "Mark Busy" : "Mark Free"}
                          </Button>
                          <Button size="sm" variant="ghost"
                            onClick={() => { if (confirm(`Remove ${spoc.name}?`)) void removeSpoc(spoc.id); }}
                            style={{ color: "#ef4444" }}>
                            ✕
                          </Button>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
