import type { ParsedEmail } from "../../../shared/types/api";
import { request } from "../../../shared/lib/api";

export interface DraftResponse {
  draft: string;
  is_followup: boolean;
  emails_in_thread: number;
}

export interface EmailSendPayload {
  to_email: string;
  subject: string;
  body: string;
}

export const commsApi = {
  fetchLatest() {
    return request<ParsedEmail[]>("/emails/latest");
  },
  generateDraft(companyId: number) {
    return request<DraftResponse>("/emails/draft", {
      method: "POST",
      body: JSON.stringify({ company_id: companyId }),
    });
  },
  send(payload: EmailSendPayload) {
    return request<{ success: boolean; message: string }>("/emails/send", {
      method: "POST",
      body: JSON.stringify(payload),
    });
  },
};
