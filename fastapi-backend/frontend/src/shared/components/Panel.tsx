import type { ReactNode } from "react";

interface PanelProps {
  title?: string;
  subtitle?: string;
  actions?: ReactNode;
  footer?: ReactNode;
  children: ReactNode;
  scrollable?: boolean;
  className?: string;
}

export function Panel({ title, subtitle, actions, footer, children, scrollable, className = "" }: PanelProps) {
  return (
    <div className={`panel ${className}`}>
      {(title || actions) && (
        <div className="panel__head">
          <div className="panel__head-left">
            {title && <h3>{title}</h3>}
            {subtitle && <p>{subtitle}</p>}
          </div>
          {actions && <div className="row">{actions}</div>}
        </div>
      )}
      <div className={`panel__body ${scrollable ? "panel__body--scroll" : ""}`}>
        {children}
      </div>
      {footer && <div className="panel__footer">{footer}</div>}
    </div>
  );
}
