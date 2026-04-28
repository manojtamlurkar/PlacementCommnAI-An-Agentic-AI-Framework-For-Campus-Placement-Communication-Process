import { useEffect, useMemo, useState } from "react";
import { companiesApi } from "../../companies/api/companiesApi";
import { logisticsApi } from "../api/logisticsApi";
import { Button } from "../../../shared/components/Button";
import { EmptyState } from "../../../shared/components/EmptyState";
import { Panel } from "../../../shared/components/Panel";
import { StatusBadge } from "../../../shared/components/StatusBadge";
import { useToast } from "../../../shared/components/ToastProvider";
import { formatDate } from "../../../shared/lib/format";
import type { Classroom, Company, LogisticsEntry } from "../../../shared/types/api";

export function LogisticsPage() {
  const { pushToast } = useToast();
  const [companies, setCompanies] = useState<Company[]>([]);
  const [classrooms, setClassrooms] = useState<Classroom[]>([]);
  const [logisticsEntries, setLogisticsEntries] = useState<LogisticsEntry[]>([]);
  const [selectedCompanyId, setSelectedCompanyId] = useState<number | null>(null);
  const [newQuestion, setNewQuestion] = useState("");
  const [questions, setQuestions] = useState<string[]>([]);
  const [activeLogisticsId, setActiveLogisticsId] = useState<number | null>(null);
  const [telegramDraft, setTelegramDraft] = useState("");
  const [classroomForm, setClassroomForm] = useState({ name: "", building: "", capacity: 80, has_projector: true });
  const [logisticsForm, setLogisticsForm] = useState({ company_id: "", drive_date: "", student_count: 100, registration_link: "" });

  const activeLogistics = useMemo(
    () => logisticsEntries.find((e) => e.id === activeLogisticsId) ?? null,
    [activeLogisticsId, logisticsEntries],
  );

  async function loadBaseData() {
    const [cl, cr] = await Promise.all([companiesApi.list(), logisticsApi.listClassrooms()]);
    setCompanies(cl); setClassrooms(cr);
  }

  async function loadLogistics(companyId: number) {
    setLogisticsEntries(await logisticsApi.getLogistics(companyId));
  }

  useEffect(() => { void loadBaseData().catch((e: Error) => pushToast(e.message, "error")); }, []);
  useEffect(() => {
    if (selectedCompanyId) {
      void loadLogistics(selectedCompanyId).catch((e: Error) => pushToast(e.message, "error"));
      setLogisticsForm((p) => ({ ...p, company_id: String(selectedCompanyId) }));
    }
  }, [selectedCompanyId]);

  async function createClassroom() {
    await logisticsApi.createClassroom({ name: classroomForm.name, building: classroomForm.building || null, capacity: Number(classroomForm.capacity), has_projector: classroomForm.has_projector });
    pushToast("Classroom added");
    setClassroomForm({ name: "", building: "", capacity: 80, has_projector: true });
    await loadBaseData();
  }

  async function createLogistics() {
    const created = await logisticsApi.createLogistics({
      company_id: Number(logisticsForm.company_id),
      drive_date: new Date(logisticsForm.drive_date).toISOString(),
      student_count: Number(logisticsForm.student_count),
      registration_link: logisticsForm.registration_link || null,
    });
    pushToast("Logistics plan created");
    setActiveLogisticsId(created.id);
    if (selectedCompanyId) await loadLogistics(selectedCompanyId);
  }

  async function saveQuestions() {
    if (!activeLogistics) { pushToast("Select a logistics entry first", "error"); return; }
    await logisticsApi.saveQuestions(activeLogistics.id, questions);
    pushToast("Follow-up questions saved");
    if (selectedCompanyId) await loadLogistics(selectedCompanyId);
  }

  async function generateTelegramDraft() {
    if (!activeLogistics) { pushToast("Select a logistics entry first", "error"); return; }
    const result = await logisticsApi.generateTelegramDraft(activeLogistics.id);
    setTelegramDraft(result.draft);
    pushToast("Telegram draft generated");
  }

  async function sendTelegramDraft() {
    if (!telegramDraft.trim()) { pushToast("Generate a draft first", "error"); return; }
    await logisticsApi.sendTelegram(telegramDraft);
    pushToast("Telegram broadcast sent");
  }

  return (
    <div>
      <div className="page-header">
        <div className="page-header__left">
          <h1>Logistics & Venues</h1>
          <p>Manage classrooms, schedule drive logistics, and broadcast Telegram announcements.</p>
        </div>
      </div>

      <div className="grid-2" style={{ marginBottom: 16 }}>
        {/* Classrooms */}
        <Panel title="Classrooms" subtitle={`${classrooms.length} rooms in inventory`}
          actions={<span className="text-muted text-xs">Auto-assigned by capacity</span>}>
          <div className="stack">
            <div className="field-grid-2">
              <div className="field"><label>Room Name</label>
                <input value={classroomForm.name} onChange={(e) => setClassroomForm((p) => ({ ...p, name: e.target.value }))} placeholder="e.g. LH1" /></div>
              <div className="field"><label>Building</label>
                <input value={classroomForm.building} onChange={(e) => setClassroomForm((p) => ({ ...p, building: e.target.value }))} placeholder="e.g. Main Block" /></div>
              <div className="field"><label>Capacity</label>
                <input type="number" value={classroomForm.capacity} onChange={(e) => setClassroomForm((p) => ({ ...p, capacity: Number(e.target.value) }))} /></div>
              <div className="field"><label>Projector</label>
                <select value={classroomForm.has_projector ? "yes" : "no"} onChange={(e) => setClassroomForm((p) => ({ ...p, has_projector: e.target.value === "yes" }))}>
                  <option value="yes">Yes</option><option value="no">No</option>
                </select></div>
            </div>
            <Button size="sm" onClick={() => void createClassroom()} disabled={!classroomForm.name}>+ Add Classroom</Button>

            {classrooms.length === 0 ? <EmptyState title="No classrooms yet" icon="🏫" /> : (
              <div className="stack-sm" style={{ marginTop: 8 }}>
                {classrooms.map((room) => (
                  <div key={room.id} className="list-item">
                    <div className="row-between">
                      <div>
                        <div className="list-item__title">{room.name}</div>
                        <div className="list-item__sub">{room.building ?? "No building"} · Cap: {room.capacity}</div>
                      </div>
                      <div className="row">
                        <StatusBadge tone={room.has_projector ? "green" : "gray"}>{room.has_projector ? "Projector" : "No Proj"}</StatusBadge>
                        <Button variant="danger" size="sm" onClick={async () => {
                          await logisticsApi.deleteClassroom(room.id);
                          pushToast("Classroom deleted");
                          await loadBaseData();
                        }}>✕</Button>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </Panel>

        {/* Drive Logistics */}
        <Panel title="Drive Logistics" subtitle="Create and manage logistics for a drive">
          <div className="stack">
            <div className="field"><label>Company</label>
              <select value={selectedCompanyId ?? ""} onChange={(e) => setSelectedCompanyId(e.target.value ? Number(e.target.value) : null)}>
                <option value="">Choose a company</option>
                {companies.map((c) => <option key={c.id} value={c.id}>{c.company_name}</option>)}
              </select>
            </div>
            <div className="field-grid-2">
              <div className="field"><label>Drive Date</label>
                <input type="date" value={logisticsForm.drive_date} onChange={(e) => setLogisticsForm((p) => ({ ...p, drive_date: e.target.value }))} /></div>
              <div className="field"><label>Expected Students</label>
                <input type="number" value={logisticsForm.student_count} onChange={(e) => setLogisticsForm((p) => ({ ...p, student_count: Number(e.target.value) }))} /></div>
            </div>
            <div className="field"><label>Registration Link</label>
              <input value={logisticsForm.registration_link} onChange={(e) => setLogisticsForm((p) => ({ ...p, registration_link: e.target.value }))} placeholder="https://..." /></div>
            <Button size="sm" onClick={() => void createLogistics()} disabled={!selectedCompanyId || !logisticsForm.drive_date}>Create Logistics Plan</Button>

            {logisticsEntries.length > 0 && (
              <div className="stack-sm" style={{ marginTop: 4 }}>
                {logisticsEntries.map((entry) => (
                  <div key={entry.id} className={`list-item list-item--clickable${activeLogisticsId === entry.id ? " list-item--active" : ""}`}
                    onClick={() => { setActiveLogisticsId(entry.id); setQuestions(entry.followup_questions ? JSON.parse(entry.followup_questions) as string[] : []); }}>
                    <div className="row-between">
                      <div><div className="list-item__title">{formatDate(entry.drive_date)}</div>
                        <div className="list-item__sub">{entry.student_count} students · Room #{entry.classroom_id ?? "TBD"}</div></div>
                      <StatusBadge tone={entry.status === "CONFIRMED" ? "green" : "amber"}>{entry.status}</StatusBadge>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </Panel>
      </div>

      {/* Active logistics detail */}
      {activeLogistics && (
        <Panel title={`Plan Details — ${formatDate(activeLogistics.drive_date)}`} subtitle="Follow-up questions and Telegram announcement">
          <div className="grid-2">
            <div className="stack">
              <div style={{ fontWeight: 600, fontSize: 13 }}>Follow-up Questions</div>
              <div className="row">
                <div className="field" style={{ flex: 1 }}>
                  <input value={newQuestion} onChange={(e) => setNewQuestion(e.target.value)} placeholder="Add a question…" onKeyDown={(e) => {
                    if (e.key === "Enter" && newQuestion.trim()) {
                      setQuestions((p) => [...p, newQuestion.trim()]); setNewQuestion("");
                    }
                  }} />
                </div>
                <Button size="sm" variant="secondary" onClick={() => { if (newQuestion.trim()) { setQuestions((p) => [...p, newQuestion.trim()]); setNewQuestion(""); } }}>Add</Button>
              </div>
              {questions.map((q, i) => (
                <div key={i} className="list-item">
                  <div className="row-between">
                    <span style={{ fontSize: 13 }}>{q}</span>
                    <Button variant="ghost" size="sm" onClick={() => setQuestions((p) => p.filter((_, j) => j !== i))}>✕</Button>
                  </div>
                </div>
              ))}
              <div className="row">
                <Button variant="secondary" size="sm" onClick={() => void saveQuestions()}>Save Questions</Button>
                <Button variant="ghost" size="sm" onClick={async () => {
                  const r = await logisticsApi.generateFollowupEmailDraft(activeLogistics.id);
                  pushToast(r.draft.slice(0, 100) + "…");
                }}>Preview Email Draft</Button>
              </div>
            </div>

            <div className="stack">
              <div style={{ fontWeight: 600, fontSize: 13 }}>Telegram Announcement</div>
              <div className="field">
                <label>Draft Message</label>
                <textarea value={telegramDraft} onChange={(e) => setTelegramDraft(e.target.value)} style={{ minHeight: 140 }} placeholder="Generate or write a Telegram announcement…" />
              </div>
              <div className="row">
                <Button variant="secondary" size="sm" onClick={() => void generateTelegramDraft()}>Generate Draft</Button>
                <Button size="sm" onClick={() => void sendTelegramDraft()} disabled={!telegramDraft.trim()}>📢 Send to Channel</Button>
              </div>
            </div>
          </div>
        </Panel>
      )}
    </div>
  );
}
