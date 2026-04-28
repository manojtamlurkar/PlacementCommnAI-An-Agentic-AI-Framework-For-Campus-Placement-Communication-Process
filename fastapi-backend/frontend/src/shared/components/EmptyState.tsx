interface EmptyStateProps { title: string; description?: string; icon?: string; }

export function EmptyState({ title, description, icon = "○" }: EmptyStateProps) {
  return (
    <div className="empty-state">
      <div className="empty-state__icon">{icon}</div>
      <div className="empty-state__title">{title}</div>
      {description && <div className="empty-state__desc">{description}</div>}
    </div>
  );
}
