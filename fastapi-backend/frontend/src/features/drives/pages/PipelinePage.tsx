import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { CompanyForm, type CompanyFormValues } from "../../companies/components/CompanyForm";
import { companiesApi } from "../../companies/api/companiesApi";
import { drivesApi } from "../api/drivesApi";
import { telegramApi } from "../../telegram/api/telegramApi";
import { Button } from "../../../shared/components/Button";
import { EmptyState } from "../../../shared/components/EmptyState";
import { LoadingBlock } from "../../../shared/components/LoadingBlock";
import { Panel } from "../../../shared/components/Panel";
import { StatusBadge, statusToneFromDriveStatus } from "../../../shared/components/StatusBadge";
import { useToast } from "../../../shared/components/ToastProvider";

import { getWorkflowIndex, workflowSteps } from "../../../shared/lib/workflow";
import type { Company, NextStepInfo, RecruitmentDrive } from "../../../shared/types/api";

type NextStepMap = Record<number, NextStepInfo | null>;
type TelegramMap = Record<number, boolean>;

function WorkflowBar({ status }: { status: string }) {
  const activeIdx = getWorkflowIndex(status);
  return (
    <div className="workflow-pipeline">
      {workflowSteps.map((step, idx) => {
        const done = idx < activeIdx;
        const active = idx === activeIdx;
        return (
          <div key={step} className="workflow-step">
            <div className={`workflow-step__node workflow-step--${done ? "done" : active ? "active" : "pending"}`}>
              <div className="workflow-step__dot" />
              <div className="workflow-step__label">{step}</div>
            </div>
            {idx < workflowSteps.length - 1 && (
              <div className={`workflow-connector${done ? " workflow-connector--done" : ""}`} />
            )}
          </div>
        );
      })}
    </div>
  );
}

export function PipelinePage() {
  const { pushToast } = useToast();
  const [companies, setCompanies] = useState<Company[]>([]);
  const [drives, setDrives] = useState<RecruitmentDrive[]>([]);
  const [nextSteps, setNextSteps] = useState<NextStepMap>({});
  const [telegramMap, setTelegramMap] = useState<TelegramMap>({});
  const [loading, setLoading] = useState(true);
  const [selectedCompanyId, setSelectedCompanyId] = useState<number | null>(null);
  const [editingCompany, setEditingCompany] = useState<Company | null>(null);
  const [showCompanyForm, setShowCompanyForm] = useState(false);
  const [driveForm, setDriveForm] = useState({ company_name: "", hr_email: "", status: "INIT" });

  const selectedCompany = useMemo(
    () => companies.find((c) => c.id === selectedCompanyId) ?? null,
    [companies, selectedCompanyId],
  );

  async function loadData() {
    setLoading(true);
    try {
      const [companyList, driveList] = await Promise.all([companiesApi.list(), drivesApi.list()]);
      setCompanies(companyList);
      setDrives(driveList);
      const [nsEntries, tgEntries] = await Promise.all([
        Promise.all(driveList.map(async (d) => {
          try { return [d.id, await drivesApi.getNextStep(d.id)] as const; }
          catch { return [d.id, null] as const; }
        })),
        Promise.all(driveList.map(async (d) => {
          try { await telegramApi.getGroup(d.id); return [d.id, true] as const; }
          catch { return [d.id, false] as const; }
        })),
      ]);
      setNextSteps(Object.fromEntries(nsEntries));
      setTelegramMap(Object.fromEntries(tgEntries));
    } catch (e) {
      pushToast(e instanceof Error ? e.message : "Failed to load pipeline", "error");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { void loadData(); }, []);
  useEffect(() => {
    if (selectedCompany) setDriveForm({ company_name: selectedCompany.company_name, hr_email: selectedCompany.email, status: "INIT" });
  }, [selectedCompany]);

  async function handleCompanySubmit(values: CompanyFormValues) {
    const payload = {
      company_name: values.company_name,
      email: values.email,
      priority: values.priority || null,
      poc_name: values.poc_name || null,
      poc_phone: values.poc_phone || null,
      poc_email: values.poc_email || null,
      location: values.location || null,
      address: values.address || null,
      description: null,
      alternate_poc_name: null,
      alternate_poc_phone: null,
      alternate_poc_email: null,
    };
    if (editingCompany) {
      await companiesApi.update(editingCompany.id, payload);
      pushToast("Company updated");
    } else {
      await companiesApi.create(payload);
      pushToast("Company created");
    }
    setEditingCompany(null);
    setShowCompanyForm(false);
    await loadData();
  }

  async function handleDriveCreate(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    await drivesApi.create(driveForm);
    pushToast("Drive created");
    await loadData();
  }

  async function triggerOutreach(driveId: number) {
    const res = await drivesApi.execute(driveId);
    pushToast(res.message);
    await loadData();
  }

  const stats = {
    total: drives.length,
    active: drives.filter((d) => !["COMPLETED", "INIT"].includes(d.status)).length,
    withSpoc: drives.filter((d) => d.spoc_name).length,
    withTelegram: Object.values(telegramMap).filter(Boolean).length,
  };

  return (
    <div>
      {/* Stats */}
      <div className="stats-row">
        {[
          { value: stats.total, label: "Total Drives", icon: "📋" },
          { value: stats.active, label: "Active Drives", icon: "🚀" },
          { value: stats.withSpoc, label: "SPOC Assigned", icon: "👤" },
          { value: stats.withTelegram, label: "Telegram Groups", icon: "💬" },
        ].map((s) => (
          <div key={s.label} className="stat-card">
            <div className="stat-card__icon">{s.icon}</div>
            <div className="stat-card__value">{s.value}</div>
            <div className="stat-card__label">{s.label}</div>
          </div>
        ))}
      </div>

      {/* Top action bar */}
      <div className="page-header">
        <div className="page-header__left">
          <h1>Recruitment Pipeline</h1>
          <p>Manage companies, create drives, and track each company through the hiring sequence.</p>
        </div>
        <div className="page-header__actions">
          <Button variant="secondary" size="sm" onClick={() => void loadData()}>↻ Refresh</Button>
          <Button variant="secondary" size="sm" onClick={() => { setEditingCompany(null); setShowCompanyForm((v) => !v); }}>
            {showCompanyForm ? "Cancel" : "+ Add Company"}
          </Button>
        </div>
      </div>

      {/* Company / Drive creation */}
      {showCompanyForm && (
        <div className="grid-2-1 section-gap" style={{ marginBottom: 20 }}>
          <Panel title={editingCompany ? "Edit Company" : "New Company"} subtitle="Fill in company details before creating a drive.">
            <CompanyForm
              initialValues={editingCompany ? {
                company_name: editingCompany.company_name,
                email: editingCompany.email,
                priority: editingCompany.priority ?? "",
                poc_name: editingCompany.poc_name ?? "",
                poc_phone: editingCompany.poc_phone ?? "",
                poc_email: editingCompany.poc_email ?? "",
                location: editingCompany.location ?? "",
                address: editingCompany.address ?? "",
              } : undefined}
              submitLabel={editingCompany ? "Update Company" : "Save Company"}
              onSubmit={handleCompanySubmit}
              onCancel={() => { setEditingCompany(null); setShowCompanyForm(false); }}
            />
          </Panel>

          <Panel title="Create Drive" subtitle="Start outreach for a company.">
            <form className="stack" onSubmit={(e) => void handleDriveCreate(e)}>
              <div className="field">
                <label>Select company</label>
                <select value={selectedCompanyId ?? ""} onChange={(e) => setSelectedCompanyId(e.target.value ? Number(e.target.value) : null)}>
                  <option value="">Choose a company</option>
                  {companies.map((c) => <option key={c.id} value={c.id}>{c.company_name}</option>)}
                </select>
              </div>
              <div className="field">
                <label>Company name</label>
                <input value={driveForm.company_name} onChange={(e) => setDriveForm((p) => ({ ...p, company_name: e.target.value }))} required />
              </div>
              <div className="field">
                <label>HR email</label>
                <input type="email" value={driveForm.hr_email} onChange={(e) => setDriveForm((p) => ({ ...p, hr_email: e.target.value }))} required />
              </div>
              <div className="field">
                <label>Initial status</label>
                <select value={driveForm.status} onChange={(e) => setDriveForm((p) => ({ ...p, status: e.target.value }))}>
                  <option value="INIT">INIT</option>
                  <option value="CONTACTED">CONTACTED</option>
                </select>
              </div>
              <Button type="submit">Create Drive</Button>
            </form>
          </Panel>
        </div>
      )}

      {/* Drives list */}
      <Panel
        title="Active Drives"
        subtitle="Click 'Open workspace' to take actions on a drive."
        actions={!loading && drives.length > 0 ? <span className="text-muted">{drives.length} drives</span> : undefined}
      >
        {loading ? (
          <LoadingBlock label="Loading drives..." />
        ) : drives.length === 0 ? (
          <EmptyState title="No drives yet" description="Add a company and create the first recruitment drive." icon="📋" />
        ) : (
          <div className="stack-sm">
            {drives.map((drive) => {
              const hasTelegram = telegramMap[drive.id] ?? false;
              const nextStep = nextSteps[drive.id];
              return (
                <article key={drive.id} className="drive-card">
                  <div className="row-between">
                    <div>
                      <div className="drive-card__company">{drive.company_name}</div>
                      <div className="drive-card__email">{drive.hr_email}</div>
                    </div>
                    <div className="row">
                      <StatusBadge tone={statusToneFromDriveStatus(drive.status)}>{drive.status}</StatusBadge>
                      <StatusBadge tone={hasTelegram ? "green" : "gray"}>
                        {hasTelegram ? "✓ Telegram" : "No Telegram"}
                      </StatusBadge>
                    </div>
                  </div>

                  {/* Workflow bar */}
                  <div style={{ marginTop: 12, marginLeft: -20, marginRight: -20 }}>
                    <WorkflowBar status={drive.status} />
                  </div>

                  <div className="drive-card__footer">
                    <div>
                      <div className="drive-card__action-hint">
                        SPOC: {drive.spoc_name ? `${drive.spoc_name}` : "Not yet assigned"}
                      </div>
                        <div className="text-muted" style={{ marginTop: 2 }}>
                        {nextStep?.next_action ? `Next: ${nextStep.next_action}` : "Open workspace for actions"}
                      </div>
                    </div>
                    <div className="row">
                      {nextStep?.next_action === "SEND_EMAIL" && (
                        <Button variant="secondary" size="sm" onClick={() => void triggerOutreach(drive.id)}>
                          Start Outreach
                        </Button>
                      )}
                      <Link className="btn btn--primary btn--sm" to={`/drives/${drive.id}`}>
                        Open Workspace →
                      </Link>
                    </div>
                  </div>
                </article>
              );
            })}
          </div>
        )}
      </Panel>
    </div>
  );
}
