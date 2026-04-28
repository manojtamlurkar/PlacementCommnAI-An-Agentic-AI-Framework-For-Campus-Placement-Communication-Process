interface StatusBadgeProps {
  tone?: "green" | "amber" | "rose" | "blue" | "purple" | "gray";
  children: React.ReactNode;
}

export function StatusBadge({ tone = "gray", children }: StatusBadgeProps) {
  return <span className={`badge badge--${tone}`}>{children}</span>;
}

export function statusToneFromDriveStatus(status: string): StatusBadgeProps["tone"] {
  switch (status) {
    case "COMPLETED": case "SPOC_HANDLING": return "green";
    case "DRIVE_CONFIRMED": case "SPOC_ASSIGNED": return "blue";
    case "CONTACTED": case "LOGISTICS_CONFIRMED": return "purple";
    case "INIT": return "gray";
    default: return "amber";
  }
}

export function statusToneFromQuestionStatus(status: string): StatusBadgeProps["tone"] {
  if (status === "HR_ANSWERED") return "green";
  if (status === "AUTO_ANSWERED") return "blue";
  if (status === "FORWARDED_TO_HR") return "purple";
  if (status === "ESCALATED" || status === "PENDING") return "amber";
  return "gray";
}
