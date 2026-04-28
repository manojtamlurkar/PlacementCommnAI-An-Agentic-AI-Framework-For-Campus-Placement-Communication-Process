import type { Classroom, LogisticsEntry } from "../../../shared/types/api";
import { request, requestData } from "../../../shared/lib/api";

export const logisticsApi = {
  listClassrooms() {
    return requestData<Classroom[]>("/classroom/all");
  },
  createClassroom(payload: {
    name: string;
    building?: string | null;
    capacity: number;
    has_projector: boolean;
  }) {
    return requestData<Classroom>("/classroom/create", {
      method: "POST",
      body: JSON.stringify(payload),
    });
  },
  deleteClassroom(id: number) {
    return requestData<null>(`/classroom/${id}`, {
      method: "DELETE",
    });
  },
  createLogistics(payload: {
    company_id: number;
    drive_date: string;
    student_count: number;
    registration_link?: string | null;
  }) {
    return requestData<LogisticsEntry>("/logistics/create", {
      method: "POST",
      body: JSON.stringify(payload),
    });
  },
  getLogistics(companyId: number) {
    return requestData<LogisticsEntry[]>(`/logistics/${companyId}`);
  },
  saveQuestions(id: number, questions: string[]) {
    return requestData<LogisticsEntry>(`/logistics/${id}/followup-questions`, {
      method: "PUT",
      body: JSON.stringify({ questions }),
    });
  },
  generateTelegramDraft(logisticsId: number) {
    return request<{ success: boolean; draft: string }>("/logistics/telegram-draft", {
      method: "POST",
      body: JSON.stringify({ logistics_id: logisticsId }),
    });
  },
  sendTelegram(message: string) {
    return request<{ success: boolean; message: string }>("/logistics/telegram-send", {
      method: "POST",
      body: JSON.stringify({ message }),
    });
  },
  generateFollowupEmailDraft(logisticsId: number) {
    return request<{ success: boolean; draft: string }>(
      "/logistics/followup-email-draft",
      {
        method: "POST",
        body: JSON.stringify({ logistics_id: logisticsId }),
      },
    );
  },
};
