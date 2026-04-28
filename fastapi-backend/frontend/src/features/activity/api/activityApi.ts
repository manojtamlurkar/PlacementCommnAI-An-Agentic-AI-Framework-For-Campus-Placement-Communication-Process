import type { ActivityLog } from "../../../shared/types/api";
import { requestData } from "../../../shared/lib/api";

export const activityApi = {
  getDriveActivity(driveId: number) {
    return requestData<ActivityLog[]>(`/activity/${driveId}`);
  },
};
