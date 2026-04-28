import { useEffect, useState } from "react";
import { approvalsApi } from "../api/approvalsApi";
import { Button } from "../../../shared/components/Button";
import { EmptyState } from "../../../shared/components/EmptyState";
import { LoadingBlock } from "../../../shared/components/LoadingBlock";
import { Panel } from "../../../shared/components/Panel";
import { StatusBadge } from "../../../shared/components/StatusBadge";
import { useToast } from "../../../shared/components/ToastProvider";
import type { Approval } from "../../../shared/types/api";

export function ApprovalsPage() {
  const { pushToast } = useToast();
  const [approvals, setApprovals] = useState<Approval[]>([]);
  const [loading, setLoading] = useState(true);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [editPayload, setEditPayload] = useState<{ subject: string; body: string; to_email: string } | null>(null);

  async function loadApprovals() {
    setLoading(true);
    try { setApprovals(await approvalsApi.listPending()); }
    catch (e) { pushToast(e instanceof Error ? e.message : "Failed", "error"); }
    finally { setLoading(false); }
  }

  async function handleAction(id: number, action: "APPROVE" | "REJECT", payloadStr?: string) {
    await approvalsApi.performAction(id, action, payloadStr);
    pushToast(`Approval ${action.toLowerCase()}d`);
    setEditingId(null);
    setEditPayload(null);
    await loadApprovals();
  }

  useEffect(() => { void loadApprovals(); }, []);

  function startEdit(a: Approval) {
    if (!a.payload) return;
    try {
      const parsed = JSON.parse(a.payload);
      setEditingId(a.id);
      setEditPayload({
        subject: parsed.subject || "",
        body: parsed.body || "",
        to_email: parsed.to_email || "",
      });
    } catch (e) {
      pushToast("Could not parse payload for editing", "error");
    }
  }

  return (
    <div>
      <div className="page-header">
        <div className="page-header__left">
          <h1>Approvals</h1>
          <p>Human-in-the-loop actions waiting for your decision before the pipeline proceeds.</p>
        </div>
        <div className="page-header__actions">
          <Button variant="secondary" size="sm" onClick={() => void loadApprovals()}>↻ Refresh</Button>
        </div>
      </div>

      <Panel title="Pending Approvals" subtitle="Approve or reject each requested action">
        {loading ? (
          <LoadingBlock label="Loading approvals..." />
        ) : approvals.length === 0 ? (
          <EmptyState title="All clear" description="No pending approvals. The orchestrator will create them as needed." icon="✓" />
        ) : (
          <div className="stack-sm">
            {approvals.map((a) => {
              const isEditing = editingId === a.id;
              let parsedPayload: any = null;
              if (a.action === "SEND_EMAIL" && a.payload && !isEditing) {
                try { parsedPayload = JSON.parse(a.payload); } catch {}
              }

              return (
              <div key={a.id} className="list-item">
                <div className="row-between" style={{ marginBottom: 8 }}>
                  <div>
                    <div className="list-item__title">{a.action}</div>
                    <div className="list-item__sub">Drive #{a.recruitment_id}</div>
                  </div>
                  <StatusBadge tone="amber">{a.status}</StatusBadge>
                </div>
                
                {isEditing && editPayload ? (
                  <div className="stack-sm" style={{ marginBottom: 12, padding: 12, background: "var(--bg-surface)", border: "1px solid var(--border)", borderRadius: "var(--radius-sm)" }}>
                    <div className="field">
                      <label>To</label>
                      <input value={editPayload.to_email} onChange={e => setEditPayload({...editPayload, to_email: e.target.value})} />
                    </div>
                    <div className="field">
                      <label>Subject</label>
                      <input value={editPayload.subject} onChange={e => setEditPayload({...editPayload, subject: e.target.value})} />
                    </div>
                    <div className="field">
                      <label>Body</label>
                      <textarea style={{ minHeight: 100 }} value={editPayload.body} onChange={e => setEditPayload({...editPayload, body: e.target.value})} />
                    </div>
                  </div>
                ) : parsedPayload ? (
                  <div style={{ marginBottom: 12, padding: 12, background: "var(--bg-surface)", border: "1px solid var(--border)", borderRadius: "var(--radius-sm)" }}>
                    <div className="text-xs text-muted" style={{ marginBottom: 4 }}>To: {parsedPayload.to_email}</div>
                    <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 8 }}>{parsedPayload.subject}</div>
                    <div style={{ fontSize: 12, whiteSpace: "pre-wrap" }}>{parsedPayload.body}</div>
                  </div>
                ) : (
                  <div className="text-muted" style={{ marginBottom: 10 }}>Resolve this to unblock the next step in the pipeline.</div>
                )}
                
                <div className="row">
                  {isEditing ? (
                    <>
                      <Button size="sm" onClick={() => void handleAction(a.id, "APPROVE", JSON.stringify(editPayload))}>Save & Approve</Button>
                      <Button variant="ghost" size="sm" onClick={() => { setEditingId(null); setEditPayload(null); }}>Cancel Edit</Button>
                    </>
                  ) : (
                    <>
                      <Button size="sm" onClick={() => void handleAction(a.id, "APPROVE")}>✓ Approve</Button>
                      {a.action === "SEND_EMAIL" && (
                        <Button variant="secondary" size="sm" onClick={() => startEdit(a)}>✏️ Edit</Button>
                      )}
                      <Button variant="danger" size="sm" onClick={() => void handleAction(a.id, "REJECT")}>✕ Reject</Button>
                    </>
                  )}
                </div>
              </div>
            )})}
          </div>
        )}
      </Panel>
    </div>
  );
}
