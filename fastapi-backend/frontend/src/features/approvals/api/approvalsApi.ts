import type { Approval } from "../../../shared/types/api";
import { requestData } from "../../../shared/lib/api";

export const approvalsApi = {
  listPending() {
    return requestData<Approval[]>("/approval/pending");
  },
  performAction(approvalId: number, action: "APPROVE" | "REJECT", payload?: string) {
    return requestData<Approval>("/approval/action", {
      method: "POST",
      body: JSON.stringify({ approval_id: approvalId, action, updated_payload: payload }),
    });
  },
};
