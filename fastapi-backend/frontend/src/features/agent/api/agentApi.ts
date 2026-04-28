import { request } from "../../../shared/lib/api";

export interface DriveAgentState {
  drive_id: number;
  company_id: number | null;
  company_name: string;
  hr_email: string;
  status: string;
  spoc_name: string | null;
  next_action: string;
  emails_sent: number;
  emails_received: number;
  has_telegram_group: boolean;
  telegram_group_name: string | null;
  telegram_invite_link: string | null;
  questions_total: number;
  questions_auto_answered: number;
  questions_forwarded: number;
  questions_hr_answered: number;
  questions_pending: number;
  latest_activity: string | null;
  latest_activity_time: string | null;
}

export interface AgentSummary {
  total_drives: number;
  active_drives: number;
  pending_actions: number;
  questions_awaiting_hr: number;
  drives: DriveAgentState[];
}

export interface RunStepResponse {
  success: boolean;
  message: string;
  action_taken: string;
}

export interface SpocPoolEntry {
  id: number;
  name: string;
  email: string;
  is_available: boolean;
  active_drives: number;
  created_at: string;
}

export interface KBEntry {
  id: number;
  category: string;
  topic: string;
  content: string;
}

export const agentApi = {
  getStatus() {
    return request<AgentSummary>("/agent/status");
  },
  runStep(driveId: number, action: string) {
    return request<RunStepResponse>(`/agent/run-step/${driveId}`, {
      method: "POST",
      body: JSON.stringify({ action }),
    });
  },
  getKnowledgeBase(companyId: number) {
    return request<KBEntry[]>(`/agent/kb/${companyId}`);
  },
  // ── SPOC Pool ──────────────────────────────────────────────────────
  listSpocs() {
    return request<SpocPoolEntry[]>("/spoc-pool/list");
  },
  addSpoc(name: string, email: string) {
    return request<SpocPoolEntry>("/spoc-pool/add", {
      method: "POST",
      body: JSON.stringify({ name, email }),
    });
  },
  removeSpoc(id: number) {
    return request<{ success: boolean; message: string }>(`/spoc-pool/${id}`, {
      method: "DELETE",
    });
  },
  toggleSpoc(id: number) {
    return request<{ success: boolean; message: string }>(`/spoc-pool/${id}/toggle`, {
      method: "PATCH",
    });
  },
};
