import { useEffect, useMemo, useState } from "react";
import { useParams } from "react-router-dom";
import { activityApi } from "../../activity/api/activityApi";
import { companiesApi } from "../../companies/api/companiesApi";
import { CompanyForm, type CompanyFormValues } from "../../companies/components/CompanyForm";
import { commsApi } from "../../comms/api/commsApi";
import { drivesApi } from "../api/drivesApi";
import { spocApi } from "../../spoc/api/spocApi";
import { telegramApi } from "../../telegram/api/telegramApi";
import { Button } from "../../../shared/components/Button";
import { EmptyState } from "../../../shared/components/EmptyState";
import { LoadingBlock } from "../../../shared/components/LoadingBlock";
import { Panel } from "../../../shared/components/Panel";
import { StatusBadge, statusToneFromDriveStatus, statusToneFromQuestionStatus } from "../../../shared/components/StatusBadge";
import { useToast } from "../../../shared/components/ToastProvider";
import { formatDateTime } from "../../../shared/lib/format";
import type { DriveWorkspaceViewModel } from "../../../shared/types/api";

export function DriveWorkspacePage() {
  const { driveId } = useParams();
  const { pushToast } = useToast();
  const [workspace, setWorkspace] = useState<DriveWorkspaceViewModel | null>(null);
  const [loading, setLoading] = useState(true);
  const [draftBody, setDraftBody] = useState("");
  const [draftSubject, setDraftSubject] = useState("");
  const [sendingEmail, setSendingEmail] = useState(false);
  const [refreshingEmails, setRefreshingEmails] = useState(false);
  const [broadcastDraft, setBroadcastDraft] = useState("");
  const [generatingBroadcast, setGeneratingBroadcast] = useState(false);
  const [refreshingQuestions, setRefreshingQuestions] = useState(false);
  const [showEditCompany, setShowEditCompany] = useState(false);
  const [spocForm, setSpocForm] = useState({ spoc_name: "", spoc_email: "" });
  const [expandedEmailId, setExpandedEmailId] = useState<number | null>(null);
  const driveNumericId = Number(driveId);

  async function loadWorkspace() {
    if (!Number.isFinite(driveNumericId)) return;
    setLoading(true);
    try {
      const [drives, companies] = await Promise.all([drivesApi.list(), companiesApi.list()]);
      const drive = drives.find((d) => d.id === driveNumericId);
      if (!drive) { setWorkspace(null); return; }
      const company = companies.find((c) => c.company_name === drive.company_name) ?? null;
      const [nextStep, emails, activity, questions] = await Promise.all([
        drivesApi.getNextStep(drive.id).catch(() => null),
        company ? companiesApi.getEmails(company.id).catch(() => []) : Promise.resolve([]),
        activityApi.getDriveActivity(drive.id).catch(() => []),
        spocApi.listQuestions(drive.id).catch(() => []),
      ]);
      let telegramGroup = null;
      try { telegramGroup = await telegramApi.getGroup(drive.id); } catch { }
      setWorkspace({ drive, company, nextStep, emails, activity, telegramGroup, questions });
      setSpocForm({ spoc_name: drive.spoc_name ?? "", spoc_email: drive.spoc_email ?? "" });
    } catch (e) {
      pushToast(e instanceof Error ? e.message : "Failed to load workspace", "error");
    } finally { setLoading(false); }
  }

  useEffect(() => { void loadWorkspace(); }, [driveNumericId]);

  const qSummary = useMemo(() => {
    if (!workspace) return { actionable: 0, all: 0 };
    return {
      actionable: workspace.questions.filter((q) => ["ESCALATED", "PENDING"].includes(q.status)).length,
      all: workspace.questions.length,
    };
  }, [workspace]);

  async function refreshEmails() {
    if (!workspace?.company) return;
    setRefreshingEmails(true);
    try {
      const updatedEmails = await companiesApi.getEmails(workspace.company.id);
      setWorkspace(prev => prev ? { ...prev, emails: updatedEmails } : null);
      pushToast("Emails refreshed");
    } catch (e) {
      pushToast(e instanceof Error ? e.message : "Failed to refresh emails", "error");
    } finally {
      setRefreshingEmails(false);
    }
  }

  async function refreshQuestions() {
    if (!workspace?.drive) return;
    setRefreshingQuestions(true);
    try {
      const updatedQuestions = await spocApi.listQuestions(workspace.drive.id);
      setWorkspace(prev => prev ? { ...prev, questions: updatedQuestions } : null);
      pushToast(`Questions refreshed — ${updatedQuestions.length} total`);
    } catch (e) {
      pushToast(e instanceof Error ? e.message : "Failed to refresh questions", "error");
    } finally {
      setRefreshingQuestions(false);
    }
  }

  async function generateDraft() {
    if (!workspace?.company) { pushToast("Company missing", "error"); return; }
    const draft = await commsApi.generateDraft(workspace.company.id);
    setDraftBody(draft.draft);
    setDraftSubject(draft.is_followup
      ? `Follow-up regarding ${workspace.drive.company_name} campus drive`
      : `Campus recruitment invitation - ${workspace.drive.company_name}`);
    pushToast("Draft generated");
  }

  async function generateTelegramBroadcast() {
    setGeneratingBroadcast(true);
    try {
      const result = await telegramApi.draftBroadcast(driveNumericId);
      setBroadcastDraft(result.draft);
      pushToast("Telegram broadcast drafted");
    } catch (e) {
      pushToast(e instanceof Error ? e.message : "Failed to draft broadcast", "error");
    } finally {
      setGeneratingBroadcast(false);
    }
  }

  async function sendDraft() {
    if (!workspace) return;
    setSendingEmail(true);
    try {
      await commsApi.send({ to_email: workspace.drive.hr_email, subject: draftSubject, body: draftBody });
      pushToast("Email queued for approval");
      setDraftBody("");
      setDraftSubject("");
      await loadWorkspace();
    } finally { setSendingEmail(false); }
  }

  async function handleCompanyUpdate(values: CompanyFormValues) {
    if (!workspace?.company) return;
    const payload = {
      company_name: values.company_name,
      email: values.email,
      priority: values.priority || null,
      poc_name: values.poc_name || null,
      poc_phone: values.poc_phone || null,
      poc_email: values.poc_email || null,
      location: values.location || null,
      address: values.address || null,
    };
    try {
      await companiesApi.update(workspace.company.id, payload);
      pushToast("Company details updated");
      setShowEditCompany(false);
      await loadWorkspace();
    } catch (e) {
      pushToast(e instanceof Error ? e.message : "Failed to update company", "error");
    }
  }

  if (loading) return <LoadingBlock label="Loading workspace..." />;
  if (!workspace) return <EmptyState title="Drive not found" description="This drive could not be loaded." />;

  const { drive, company, nextStep, emails, activity, telegramGroup, questions } = workspace;

  return (
    <div>
      <div className="page-header">
        <div className="page-header__left">
          <h1>{drive.company_name}</h1>
          <p>Drive workspace — status, comms, SPOC handoff, Telegram, and activity all in one place.</p>
        </div>
        <div className="page-header__actions">
          <StatusBadge tone={statusToneFromDriveStatus(drive.status)}>{drive.status}</StatusBadge>
          <StatusBadge tone={telegramGroup ? "green" : "gray"}>
            {telegramGroup ? "✓ Telegram" : "No Group"}
          </StatusBadge>
          {company && (
            <Button variant="secondary" size="sm" onClick={() => setShowEditCompany((v) => !v)}>
              {showEditCompany ? "Cancel Edit" : "✏️ Edit Company"}
            </Button>
          )}
          <Button variant="secondary" size="sm" onClick={() => void loadWorkspace()}>↻ Refresh</Button>
        </div>
      </div>

      {/* Edit Company Form */}
      {showEditCompany && company && (
        <div className="section-gap" style={{ marginBottom: 16 }}>
          <Panel title="Edit Company Details">
            <CompanyForm
              initialValues={{
                company_name: company.company_name,
                email: company.email,
                priority: company.priority ?? "",
                poc_name: company.poc_name ?? "",
                poc_phone: company.poc_phone ?? "",
                poc_email: company.poc_email ?? "",
                location: company.location ?? "",
                address: company.address ?? "",
              }}
              submitLabel="Update Details"
              onSubmit={handleCompanyUpdate}
              onCancel={() => setShowEditCompany(false)}
            />
          </Panel>
        </div>
      )}

      {/* Row 1: Overview + Actions */}
      <div className="grid-2" style={{ marginBottom: 16 }}>
        <Panel title="Drive Overview">
          <div className="stack">
            {/* Meta info */}
            <div className="grid-2-1" style={{ gap: 8 }}>
              {[
                { label: "HR Email", value: drive.hr_email },
                { label: "SPOC", value: drive.spoc_name ? `${drive.spoc_name} · ${drive.spoc_email}` : "Not assigned" },
                { label: "Telegram", value: telegramGroup ? telegramGroup.group_name : "Not created" },
                { label: "Questions", value: `${qSummary.actionable} need action / ${qSummary.all} total` },
              ].map((m) => (
                <div key={m.label} style={{ background: "var(--bg-surface)", borderRadius: "var(--radius-sm)", padding: "10px 12px", border: "1px solid var(--border)" }}>
                  <div className="text-xs" style={{ color: "var(--text-muted)", marginBottom: 3 }}>{m.label}</div>
                  <div style={{ fontSize: 13, fontWeight: 500, color: "var(--text-primary)" }}>{m.value}</div>
                </div>
              ))}
            </div>
            {nextStep && (
              <div style={{ background: "var(--accent-light)", border: "1px solid rgba(99,102,241,0.25)", borderRadius: "var(--radius-sm)", padding: "10px 12px" }}>
                <div className="text-xs" style={{ color: "var(--text-muted)", marginBottom: 3 }}>Recommended next action</div>
                <div style={{ fontSize: 13, fontWeight: 600, color: "var(--text-accent)" }}>
                  {nextStep.next_action ?? "All caught up"}
                </div>
              </div>
            )}
          </div>
        </Panel>

        <Panel title="Actions">
          <div className="stack">
            {/* HR Email */}
            <div style={{ border: "1px solid var(--border)", borderRadius: "var(--radius-sm)", padding: 14 }}>
              <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10 }}>HR Communication</div>
              <div className="stack-sm">
                <div className="field">
                  <label>Subject</label>
                  <input value={draftSubject} onChange={(e) => setDraftSubject(e.target.value)} placeholder="Email subject…" />
                </div>
                <div className="field">
                  <label>Body</label>
                  <textarea value={draftBody} onChange={(e) => setDraftBody(e.target.value)} style={{ minHeight: 80 }} placeholder="Email body…" />
                </div>
                <div className="row">
                  <Button variant="secondary" size="sm" onClick={() => void generateDraft()}>Generate Draft</Button>
                  <Button size="sm" onClick={() => void sendDraft()} disabled={!draftBody.trim() || !draftSubject.trim() || sendingEmail}>
                    {sendingEmail ? "Sending…" : "Send Email"}
                  </Button>
                </div>
              </div>
            </div>

            {/* Confirm Drive */}
            <div style={{ border: "1px solid var(--border)", borderRadius: "var(--radius-sm)", padding: 14 }}>
              <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 6 }}>Confirm Drive</div>
              <div className="text-muted" style={{ marginBottom: 10 }}>Use after HR confirms participation.</div>
              <Button variant="secondary" size="sm"
                onClick={async () => { await drivesApi.confirm(drive.id); pushToast("Drive confirmed"); await loadWorkspace(); }}
                disabled={["DRIVE_CONFIRMED","SPOC_ASSIGNED","SPOC_HANDLING"].includes(drive.status)}>
                Confirm Drive
              </Button>
            </div>

            {/* SPOC */}
            <div style={{ border: "1px solid var(--border)", borderRadius: "var(--radius-sm)", padding: 14 }}>
              <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 8 }}>Assign SPOC</div>
              <div className="field-grid-2" style={{ marginBottom: 8 }}>
                <div className="field">
                  <label>Name</label>
                  <input value={spocForm.spoc_name} onChange={(e) => setSpocForm((p) => ({ ...p, spoc_name: e.target.value }))} />
                </div>
                <div className="field">
                  <label>Email</label>
                  <input type="email" value={spocForm.spoc_email} onChange={(e) => setSpocForm((p) => ({ ...p, spoc_email: e.target.value }))} />
                </div>
              </div>
              <Button size="sm"
                onClick={async () => { await drivesApi.assignSpoc(drive.id, spocForm); pushToast("SPOC assigned"); await loadWorkspace(); }}
                disabled={!spocForm.spoc_name.trim() || !spocForm.spoc_email.trim()}>
                Assign SPOC
              </Button>
            </div>

            {/* Telegram */}
            <div style={{ border: "1px solid var(--border)", borderRadius: "var(--radius-sm)", padding: 14 }}>
              <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 6 }}>Telegram Group</div>
              {telegramGroup ? (
                <div className="text-muted" style={{ marginBottom: 8, fontSize: 12 }}>
                  {telegramGroup.group_name}
                  {telegramGroup.invite_link && <> · <a href={telegramGroup.invite_link} target="_blank" rel="noreferrer" style={{ color: "var(--text-accent)" }}>Join link</a></>}
                </div>
              ) : (
                <div className="text-muted" style={{ marginBottom: 8, fontSize: 12 }}>No group created yet.</div>
              )}
              <div className="row" style={{ marginBottom: 12 }}>
                <Button variant="secondary" size="sm"
                  onClick={async () => { await telegramApi.createGroup(drive.id); pushToast("Telegram group created"); await loadWorkspace(); }}>
                  {telegramGroup ? "Recheck Group" : "Create Group"}
                </Button>
                {telegramGroup?.invite_link && (
                  <Button variant="secondary" size="sm" onClick={() => void generateTelegramBroadcast()} disabled={generatingBroadcast}>
                    {generatingBroadcast ? "Generating..." : "Draft Broadcast"}
                  </Button>
                )}
              </div>
              
              {telegramGroup?.invite_link && broadcastDraft && (
                <div className="stack-sm" style={{ marginTop: 12, borderTop: "1px solid var(--border)", paddingTop: 12 }}>
                  <div className="field">
                    <label>Broadcast Message</label>
                    <textarea 
                      value={broadcastDraft} 
                      onChange={(e) => setBroadcastDraft(e.target.value)} 
                      style={{ minHeight: 120, fontSize: 13 }} 
                      placeholder="Click 'Draft Broadcast' to generate or type your own message..." 
                    />
                  </div>
                  <Button size="sm"
                    disabled={!broadcastDraft.trim()}
                    onClick={async () => { 
                      await telegramApi.broadcastInvite({ invite_link: telegramGroup.invite_link!, company_name: drive.company_name, custom_message: broadcastDraft }); 
                      pushToast("Invite broadcasted"); 
                    }}>
                    📢 Broadcast to Main Channel
                  </Button>
                </div>
              )}
            </div>
          </div>
        </Panel>
      </div>

      {/* Row 2: Comms + Questions */}
      <div className="grid-2" style={{ marginBottom: 16 }}>
        <Panel 
          title="Email Thread" 
          subtitle={`${emails.length} emails`} 
          scrollable
          actions={
            <Button variant="secondary" size="sm" onClick={() => void refreshEmails()} disabled={refreshingEmails}>
              {refreshingEmails ? "↻ Refreshing..." : "↻ Sync Mails"}
            </Button>
          }
        >
          {emails.length === 0 ? (
            <EmptyState title="No emails yet" icon="✉️" />
          ) : (
            emails.map((email) => {
              const isExpanded = expandedEmailId === email.id;
              return (
              <div 
                key={email.id} 
                className="email-card" 
                onClick={() => setExpandedEmailId(isExpanded ? null : email.id)}
                style={{ cursor: "pointer", transition: "all 0.2s ease" }}
              >
                <div className="row-between">
                  <div className="email-card__subject">{email.subject || "Untitled"}</div>
                  <StatusBadge tone={email.direction === "SENT" ? "blue" : "green"}>{email.direction}</StatusBadge>
                </div>
                <div 
                  className={isExpanded ? "" : "email-card__body"} 
                  style={isExpanded ? { whiteSpace: "pre-wrap", fontSize: 13, marginTop: 8, color: "var(--text-primary)", wordBreak: "break-word" } : {}}
                >
                  {email.body}
                </div>
                <div className="email-card__meta" style={{ marginTop: isExpanded ? 12 : undefined }}>
                  {formatDateTime(email.timestamp)}
                </div>
              </div>
            )})
          )}
        </Panel>

        <Panel 
          title="Student Questions" 
          subtitle={`${qSummary.actionable} need attention · ${qSummary.all} total`} 
          scrollable
          actions={
            <Button variant="secondary" size="sm" onClick={() => void refreshQuestions()} disabled={refreshingQuestions}>
              {refreshingQuestions ? "↻ Refreshing..." : "↻ Refresh"}
            </Button>
          }
        >
          {questions.length === 0 ? (
            <EmptyState title="No questions yet" description="Questions appear once the Telegram group is active and students start messaging." icon="💬" />
          ) : (
            <div className="stack-sm">
              {questions.map((q) => (
                <div key={q.id} className="list-item" style={{ gap: 6 }}>
                  <div className="row-between">
                    <div className="list-item__title">@{q.telegram_user}</div>
                    <StatusBadge tone={statusToneFromQuestionStatus(q.status)}>{q.status}</StatusBadge>
                  </div>
                  <div className="list-item__body" style={{ fontWeight: 500 }}>{q.question_text}</div>
                  {q.auto_answer && (
                    <div style={{ fontSize: 12, color: "var(--text-muted)", background: "var(--bg-surface)", borderRadius: "var(--radius-sm)", padding: "6px 8px", borderLeft: "3px solid var(--text-accent)" }}>
                      <span style={{ fontWeight: 600, color: "var(--text-accent)" }}>AI: </span>{q.auto_answer}
                    </div>
                  )}
                  {q.hr_answer && (
                    <div style={{ fontSize: 12, color: "var(--text-muted)", background: "var(--bg-surface)", borderRadius: "var(--radius-sm)", padding: "6px 8px", borderLeft: "3px solid #22c55e" }}>
                      <span style={{ fontWeight: 600, color: "#22c55e" }}>HR: </span>{q.hr_answer}
                    </div>
                  )}
                  <div className="text-xs" style={{ color: "var(--text-muted)", marginTop: 2 }}>{formatDateTime(q.created_at)}</div>
                </div>
              ))}
            </div>
          )}
        </Panel>
      </div>

      {/* Row 3: Activity timeline */}
      <Panel title="Activity Timeline" subtitle="Full audit trail for this drive." scrollable>
        {activity.length === 0 ? (
          <EmptyState title="No activity yet" description="Activity logs appear as you take actions." icon="📊" />
        ) : (
          <div className="timeline">
            {activity.map((entry) => {
              const dotClass = entry.actor === "ORCHESTRATOR" ? "timeline-dot" : entry.actor === "SPOC" ? "timeline-dot--green" : "timeline-dot--gray";
              return (
                <div key={entry.id} className="timeline-item">
                  <span className={`timeline-dot ${dotClass}`} />
                  <div style={{ flex: 1 }}>
                    <div className="row-between">
                      <div className="timeline-item__action">{entry.action}</div>
                      <StatusBadge tone="gray">{entry.actor}</StatusBadge>
                    </div>
                    <div className="timeline-item__details">{entry.details}</div>
                    <div className="timeline-item__meta">{formatDateTime(entry.timestamp)}</div>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </Panel>

      {company && <p className="text-muted" style={{ marginTop: 12, textAlign: "right" }}>Company: {company.company_name} · {company.location ?? "Location N/A"}</p>}
    </div>
  );
}
