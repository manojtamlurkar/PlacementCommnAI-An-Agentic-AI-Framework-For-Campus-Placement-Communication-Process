import type { RecruitmentDrive } from "../types/api";

export const workflowSteps = [
  "Company Setup",
  "Drive Created",
  "HR Contact",
  "Drive Confirmed",
  "SPOC Assigned",
  "Telegram Ready",
  "SPOC Handling",
] as const;

const statusIndexMap: Record<string, number> = {
  INIT: 1,
  CONTACTED: 2,
  WAIT_FOR_REPLY: 2,
  DRIVE_CONFIRMED: 3,
  LOGISTICS_CONFIRMED: 3,
  SPOC_ASSIGNED: 4,
  SPOC_HANDLING: 6,
  MONITOR_DRIVE: 6,
  COMPLETED: 6,
  DONE: 6,
};

export function getWorkflowIndex(status: string) {
  return statusIndexMap[status] ?? 1;
}

export function getDriveActionLabel(
  drive: RecruitmentDrive,
  nextAction: string | null | undefined,
  hasTelegramGroup: boolean,
) {
  if (drive.status === "DRIVE_CONFIRMED" && !drive.spoc_name) {
    return "Assign SPOC";
  }
  if (drive.spoc_name && !hasTelegramGroup) {
    return "Create Telegram Group";
  }
  if (drive.status === "CONTACTED") {
    return "Confirm HR Reply";
  }
  if (nextAction === "SEND_EMAIL") {
    return "Start Outreach";
  }
  if (nextAction === "WAIT_FOR_REPLY") {
    return "Await HR Reply";
  }
  if (drive.status === "SPOC_ASSIGNED") {
    return "Prepare SPOC Handoff";
  }
  if (drive.status === "SPOC_HANDLING") {
    return "Review SPOC Queue";
  }
  return "Open Workspace";
}
