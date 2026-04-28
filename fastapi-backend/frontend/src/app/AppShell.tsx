import { NavLink, Route, Routes, useLocation } from "react-router-dom";
import { NotificationBell } from "../shared/components/NotificationBell";
import { ActivityPage } from "../features/activity/pages/ActivityPage";
import { AgentConsolePage } from "../features/agent/pages/AgentConsolePage";
import { ApprovalsPage } from "../features/approvals/pages/ApprovalsPage";
import { DriveWorkspacePage } from "../features/drives/pages/DriveWorkspacePage";
import { PipelinePage } from "../features/drives/pages/PipelinePage";
import { LogisticsPage } from "../features/logistics/pages/LogisticsPage";
import { SpocPage } from "../features/spoc/pages/SpocPage";

const PAGE_TITLES: Record<string, string> = {
  "/": "Recruitment Pipeline",
  "/agent": "Agent Console",
  "/spoc": "SPOC Queue",
  "/approvals": "Approvals",
  "/logistics": "Logistics",
  "/activity": "Activity Log",
};

function usePageTitle() {
  const { pathname } = useLocation();
  if (pathname.startsWith("/drives/")) return "Drive Workspace";
  return PAGE_TITLES[pathname] ?? "CDC Recruitment";
}

const navItems = [
  {
    to: "/",
    label: "Pipeline",
    icon: (
      <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5">
        <rect x="1" y="1" width="6" height="6" rx="1.5"/>
        <rect x="9" y="1" width="6" height="6" rx="1.5"/>
        <rect x="1" y="9" width="6" height="6" rx="1.5"/>
        <rect x="9" y="9" width="6" height="6" rx="1.5"/>
      </svg>
    ),
  },
  {
    to: "/agent",
    label: "Agent Console",
    icon: (
      <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5">
        <circle cx="8" cy="5" r="3"/>
        <path d="M5 5h6M8 2v6M3 14c0-2.8 2.2-5 5-5s5 2.2 5 5"/>
      </svg>
    ),
  },
  {
    to: "/spoc",
    label: "SPOC Queue",
    icon: (
      <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5">
        <path d="M14 10.5c0 2-1.5 3-3 3L8 15l.5-1.5C6 13 2 11.5 2 8V6c0-2.5 2-4 5-4s5 1.5 5 4v2c0 .17-.01.34-.03.5H14z"/>
      </svg>
    ),
  },
  {
    to: "/approvals",
    label: "Approvals",
    icon: (
      <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5">
        <path d="M8 1L10 5.5H15L11 8.5L12.5 13L8 10L3.5 13L5 8.5L1 5.5H6L8 1Z"/>
      </svg>
    ),
  },
  {
    to: "/logistics",
    label: "Logistics",
    icon: (
      <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5">
        <rect x="1" y="4" width="14" height="10" rx="1.5"/>
        <path d="M1 7h14M5 4V2M11 4V2"/>
      </svg>
    ),
  },
  {
    to: "/activity",
    label: "Activity",
    icon: (
      <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5">
        <path d="M1 8h3l2-5 3 9 2-5 1.5 1H15"/>
      </svg>
    ),
  },
];

export function AppShell() {
  const title = usePageTitle();
  const { pathname } = useLocation();

  return (
    <div className="app">
      {/* ── SIDEBAR ── */}
      <aside className="sidebar">
        <div className="sidebar__brand">
          <div className="sidebar__brand-logo">
            <div className="sidebar__brand-icon">C</div>
            <span className="sidebar__brand-name">CDC Recruit</span>
          </div>
          <div className="sidebar__brand-sub">NITK Surathkal</div>
        </div>

        <nav className="sidebar__nav">
          <div className="sidebar__section-label">Navigation</div>
          {navItems.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.to === "/"}
              className={({ isActive }) => `nav-link${isActive || (item.to !== "/" && pathname.startsWith(item.to)) ? " active" : ""}`}
            >
              <span className="nav-link__icon">{item.icon}</span>
              {item.label}
            </NavLink>
          ))}
        </nav>

        <div className="sidebar__footer">
          <div className="sidebar__status">
            <span className="status-dot" />
            Backend connected
          </div>
        </div>
      </aside>

      {/* ── MAIN ── */}
      <div className="main">
        <header className="topbar">
          {pathname.startsWith("/drives/") && (
            <NavLink to="/" className="topbar__back">
              <svg width="14" height="14" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M10 12L6 8l4-4"/>
              </svg>
              Pipeline
            </NavLink>
          )}
          <span className="topbar__title">{title}</span>
          <span className="topbar__sub">Agentic AI Framework • FastAPI + React</span>
          <div style={{ marginLeft: "auto" }}>
            <NotificationBell />
          </div>
        </header>

        <main className="page-content">
          <Routes>
            <Route path="/" element={<PipelinePage />} />
            <Route path="/agent" element={<AgentConsolePage />} />
            <Route path="/drives/:driveId" element={<DriveWorkspacePage />} />
            <Route path="/spoc" element={<SpocPage />} />
            <Route path="/approvals" element={<ApprovalsPage />} />
            <Route path="/logistics" element={<LogisticsPage />} />
            <Route path="/activity" element={<ActivityPage />} />
          </Routes>
        </main>
      </div>
    </div>
  );
}
