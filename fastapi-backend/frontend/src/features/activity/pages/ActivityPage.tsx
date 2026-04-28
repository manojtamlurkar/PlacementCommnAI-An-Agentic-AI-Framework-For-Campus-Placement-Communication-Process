import { useEffect, useState } from "react";
import { activityApi } from "../api/activityApi";
import { drivesApi } from "../../drives/api/drivesApi";
import { Button } from "../../../shared/components/Button";
import { EmptyState } from "../../../shared/components/EmptyState";
import { LoadingBlock } from "../../../shared/components/LoadingBlock";
import { Panel } from "../../../shared/components/Panel";
import { StatusBadge } from "../../../shared/components/StatusBadge";
import { useToast } from "../../../shared/components/ToastProvider";
import { formatDateTime } from "../../../shared/lib/format";
import type { ActivityLog, RecruitmentDrive } from "../../../shared/types/api";

const ACTOR_TONE: Record<string, "purple" | "green" | "blue" | "amber" | "gray"> = {
  ORCHESTRATOR: "purple", SPOC: "green", AGENT: "blue", SYSTEM: "amber", USER: "gray",
};

export function ActivityPage() {
  const { pushToast } = useToast();
  const [drives, setDrives] = useState<RecruitmentDrive[]>([]);
  const [selectedDriveId, setSelectedDriveId] = useState<number | null>(null);
  const [activity, setActivity] = useState<ActivityLog[]>([]);
  const [loading, setLoading] = useState(true);

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

  async function loadActivity(driveId: number) {
    try { setActivity(await activityApi.getDriveActivity(driveId)); }
    catch (e) { pushToast(e instanceof Error ? e.message : "Failed", "error"); }
  }

  useEffect(() => { void loadDrives(); }, []);
  useEffect(() => { if (selectedDriveId) void loadActivity(selectedDriveId); }, [selectedDriveId]);

  if (loading) return <LoadingBlock label="Loading activity..." />;

  const selectedDrive = drives.find((d) => d.id === selectedDriveId);

  return (
    <div>
      <div className="page-header">
        <div className="page-header__left">
          <h1>Activity Log</h1>
          <p>Full chronological audit trail — every orchestrator event, email, and agent action.</p>
        </div>
        <div className="page-header__actions">
          <div className="field" style={{ width: 240 }}>
            <select value={selectedDriveId ?? ""} onChange={(e) => setSelectedDriveId(Number(e.target.value))}>
              {drives.map((d) => <option key={d.id} value={d.id}>{d.company_name} — {d.status}</option>)}
            </select>
          </div>
          <Button variant="secondary" size="sm" onClick={() => selectedDriveId && void loadActivity(selectedDriveId)}>↻ Refresh</Button>
        </div>
      </div>

      <Panel
        title={selectedDrive ? `${selectedDrive.company_name} — Activity` : "Activity Timeline"}
        subtitle={`${activity.length} events recorded`}
        scrollable
      >
        {activity.length === 0 ? (
          <EmptyState title="No activity yet" description="Events appear as you confirm drives, send emails, and assign SPOCs." icon="📊" />
        ) : (
          <div className="timeline">
            {[...activity].reverse().map((entry) => {
              const dotCls = entry.action === "STALE_ALERT" ? "timeline-dot--amber"
                : entry.actor === "ORCHESTRATOR" ? "timeline-dot"
                : entry.actor === "SPOC" || entry.actor === "AGENT" ? "timeline-dot--green"
                : "timeline-dot--gray";
              return (
                <div key={entry.id} className="timeline-item">
                  <span className={`timeline-dot ${dotCls}`} />
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div className="row-between">
                      <div className="timeline-item__action">{entry.action}</div>
                      <StatusBadge tone={ACTOR_TONE[entry.actor] ?? "gray"}>{entry.actor}</StatusBadge>
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
    </div>
  );
}
