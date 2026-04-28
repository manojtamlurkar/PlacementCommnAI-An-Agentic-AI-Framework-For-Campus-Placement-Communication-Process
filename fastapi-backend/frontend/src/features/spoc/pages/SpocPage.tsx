import { useEffect, useMemo, useState } from "react";
import { drivesApi } from "../../drives/api/drivesApi";
import { spocApi } from "../api/spocApi";
import { Button } from "../../../shared/components/Button";
import { EmptyState } from "../../../shared/components/EmptyState";
import { LoadingBlock } from "../../../shared/components/LoadingBlock";
import { Panel } from "../../../shared/components/Panel";
import { StatusBadge, statusToneFromQuestionStatus } from "../../../shared/components/StatusBadge";
import { useToast } from "../../../shared/components/ToastProvider";
import type { RecruitmentDrive, StudentQuestion } from "../../../shared/types/api";

export function SpocPage() {
  const { pushToast } = useToast();
  const [drives, setDrives] = useState<RecruitmentDrive[]>([]);
  const [selectedDriveId, setSelectedDriveId] = useState<number | null>(null);
  const [questions, setQuestions] = useState<StudentQuestion[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedQuestionIds, setSelectedQuestionIds] = useState<number[]>([]);
  const [answerText, setAnswerText] = useState("");
  const [activeQuestionId, setActiveQuestionId] = useState<number | null>(null);

  async function loadDrives() {
    setLoading(true);
    try {
      const list = await drivesApi.list();
      setDrives(list);
      if (!selectedDriveId && list.length > 0) setSelectedDriveId(list[0].id);
    } catch (e) {
      pushToast(e instanceof Error ? e.message : "Failed", "error");
    } finally { setLoading(false); }
  }

  async function loadQuestions(driveId: number) {
    try {
      const data = await spocApi.listQuestions(driveId);
      setQuestions(data);
      setSelectedQuestionIds([]);
    } catch (e) {
      pushToast(e instanceof Error ? e.message : "Failed to load questions", "error");
    }
  }

  useEffect(() => { void loadDrives(); }, []);
  useEffect(() => { if (selectedDriveId) void loadQuestions(selectedDriveId); }, [selectedDriveId]);

  const actionable = useMemo(() => questions.filter((q) => ["ESCALATED", "PENDING"].includes(q.status)), [questions]);
  const activeQ = questions.find((q) => q.id === activeQuestionId) ?? null;

  async function forwardSelected() {
    if (!selectedDriveId || selectedQuestionIds.length === 0) { pushToast("Select at least one question", "error"); return; }
    await spocApi.forwardToHr(selectedDriveId, selectedQuestionIds);
    pushToast("Questions forwarded to HR");
    await loadQuestions(selectedDriveId);
  }

  async function submitAnswer() {
    if (!selectedDriveId || !activeQuestionId || !answerText.trim()) { pushToast("Choose a question and write an answer", "error"); return; }
    await spocApi.answerQuestion(selectedDriveId, activeQuestionId, answerText);
    pushToast("Answer posted to Telegram");
    setAnswerText("");
    setActiveQuestionId(null);
    await loadQuestions(selectedDriveId);
  }

  if (loading) return <LoadingBlock label="Loading SPOC queue..." />;

  return (
    <div>
      <div className="page-header">
        <div className="page-header__left">
          <h1>SPOC Queue</h1>
          <p>Review escalated questions, forward to HR in bulk, or post answers directly to Telegram.</p>
        </div>
        <div className="page-header__actions">
          <div className="field" style={{ width: 220 }}>
            <select value={selectedDriveId ?? ""} onChange={(e) => setSelectedDriveId(Number(e.target.value))}>
              {drives.map((d) => <option key={d.id} value={d.id}>{d.company_name}</option>)}
            </select>
          </div>
          <Button variant="secondary" size="sm" onClick={() => selectedDriveId && void loadQuestions(selectedDriveId)}>↻ Refresh</Button>
        </div>
      </div>

      {/* Summary chips */}
      <div className="stats-row" style={{ gridTemplateColumns: "repeat(3, 1fr)", marginBottom: 16 }}>
        {[
          { value: questions.length, label: "Total Questions", icon: "❓" },
          { value: actionable.length, label: "Need Action", icon: "⚠️" },
          { value: questions.filter((q) => q.status === "HR_ANSWERED").length, label: "Answered", icon: "✓" },
        ].map((s) => (
          <div key={s.label} className="stat-card">
            <div className="stat-card__icon">{s.icon}</div>
            <div className="stat-card__value">{s.value}</div>
            <div className="stat-card__label">{s.label}</div>
          </div>
        ))}
      </div>

      <div className="grid-2">
        {/* Queue */}
        <Panel
          title="Question Queue"
          subtitle="Select questions to batch-forward to HR"
          actions={
            <Button size="sm" onClick={() => void forwardSelected()} disabled={selectedQuestionIds.length === 0}>
              Forward {selectedQuestionIds.length > 0 ? `(${selectedQuestionIds.length})` : ""} to HR
            </Button>
          }
          scrollable
        >
          {questions.length === 0 ? (
            <EmptyState title="No questions yet" description="Questions appear once students message in the Telegram group." icon="💬" />
          ) : (
            <div className="stack-sm">
              {questions.map((q) => {
                const isActionable = ["ESCALATED", "PENDING"].includes(q.status);
                const isActive = activeQuestionId === q.id;
                return (
                  <div
                    key={q.id}
                    className={`list-item list-item--clickable${isActive ? " list-item--active" : ""}`}
                    onClick={() => { setActiveQuestionId(q.id); setAnswerText(q.hr_answer ?? ""); }}
                  >
                    <div className="row-between" style={{ marginBottom: 6 }}>
                      <div className="list-item__title">@{q.telegram_user}</div>
                      <StatusBadge tone={statusToneFromQuestionStatus(q.status)}>{q.status}</StatusBadge>
                    </div>
                    <div className="list-item__body">{q.question_text}</div>
                    {q.auto_answer && (
                      <div style={{ marginTop: 6, fontSize: 12, color: "var(--blue)", background: "var(--blue-bg)", padding: "6px 8px", borderRadius: "var(--radius-sm)" }}>
                        Auto: {q.auto_answer}
                      </div>
                    )}
                    {isActionable && (
                      <label className="row" style={{ marginTop: 8, cursor: "pointer" }} onClick={(e) => e.stopPropagation()}>
                        <input
                          type="checkbox"
                          checked={selectedQuestionIds.includes(q.id)}
                          onChange={(e) => {
                            setSelectedQuestionIds((prev) =>
                              e.target.checked ? [...prev, q.id] : prev.filter((id) => id !== q.id)
                            );
                          }}
                        />
                        <span className="text-muted">Include in HR batch</span>
                      </label>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </Panel>

        {/* Answer panel */}
        <Panel title="Answer Panel" subtitle="Post a manual reply to Telegram">
          {activeQ ? (
            <div className="stack">
              <div style={{ background: "var(--bg-surface)", border: "1px solid var(--border)", borderRadius: "var(--radius-sm)", padding: 14 }}>
                <div className="text-xs" style={{ color: "var(--text-muted)", marginBottom: 4 }}>Selected Question</div>
                <div style={{ fontSize: 13, fontWeight: 500, color: "var(--text-primary)" }}>@{activeQ.telegram_user}</div>
                <div className="list-item__body">{activeQ.question_text}</div>
                <div style={{ marginTop: 6 }}>
                  <StatusBadge tone={statusToneFromQuestionStatus(activeQ.status)}>{activeQ.status}</StatusBadge>
                </div>
              </div>
              <div className="field">
                <label>Answer to post to Telegram</label>
                <textarea
                  value={answerText}
                  onChange={(e) => setAnswerText(e.target.value)}
                  placeholder="Write the answer that will be sent back to the student in the Telegram group…"
                  style={{ minHeight: 140 }}
                />
              </div>
              <div className="row">
                <Button onClick={() => void submitAnswer()} disabled={!answerText.trim()}>
                  Post to Telegram
                </Button>
                <Button variant="ghost" size="sm" onClick={() => { setActiveQuestionId(null); setAnswerText(""); }}>
                  Cancel
                </Button>
              </div>
            </div>
          ) : (
            <EmptyState title="Select a question" description="Click a question from the queue to draft and post the reply." icon="👆" />
          )}

          {actionable.length > 0 && (
            <div style={{ marginTop: 20, paddingTop: 16, borderTop: "1px solid var(--border)" }}>
              <div style={{ fontSize: 12, fontWeight: 600, color: "var(--text-secondary)", marginBottom: 8 }}>Need Action</div>
              <div className="stack-sm">
                {actionable.slice(0, 3).map((q) => (
                  <div key={q.id} className="row-between" style={{ fontSize: 12 }}>
                    <span style={{ color: "var(--text-secondary)", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", flex: 1 }}>
                      @{q.telegram_user}: {q.question_text.slice(0, 40)}…
                    </span>
                    <StatusBadge tone="amber">{q.status}</StatusBadge>
                  </div>
                ))}
                {actionable.length > 3 && <div className="text-muted">+{actionable.length - 3} more</div>}
              </div>
            </div>
          )}
        </Panel>
      </div>
    </div>
  );
}
