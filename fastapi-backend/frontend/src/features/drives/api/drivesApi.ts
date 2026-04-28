import type { NextStepInfo, RecruitmentDrive } from "../../../shared/types/api";
import { request, requestData } from "../../../shared/lib/api";
import type { StandardResponse } from "../../../shared/types/api";

export interface DrivePayload {
  company_name: string;
  hr_email: string;
  status: string;
}

export interface AssignSpocPayload {
  spoc_name: string;
  spoc_email: string;
}

export const drivesApi = {
  list() {
    return requestData<RecruitmentDrive[]>("/recruitment/all");
  },
  create(payload: DrivePayload) {
    return requestData<RecruitmentDrive>("/recruitment/create", {
      method: "POST",
      body: JSON.stringify(payload),
    });
  },
  getNextStep(id: number) {
    return requestData<NextStepInfo>(`/recruitment/next-step/${id}`);
  },
  execute(id: number) {
    return request<StandardResponse<{ approval_id?: number } | null>>(
      `/recruitment/execute/${id}`,
      {
        method: "POST",
      },
    );
  },
  confirm(id: number) {
    return requestData<RecruitmentDrive>(`/recruitment/confirm-drive/${id}`, {
      method: "PATCH",
    });
  },
  assignSpoc(id: number, payload: AssignSpocPayload) {
    return requestData<RecruitmentDrive>(`/recruitment/assign-spoc/${id}`, {
      method: "PUT",
      body: JSON.stringify(payload),
    });
  },
};
