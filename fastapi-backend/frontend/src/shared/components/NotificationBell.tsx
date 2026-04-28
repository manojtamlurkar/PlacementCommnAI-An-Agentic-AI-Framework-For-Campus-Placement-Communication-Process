import { useState, useRef, useEffect } from "react";
import { useNotifications } from "./NotificationProvider";

function formatRelativeTime(iso: string | null): string {
  if (!iso) return "";
  const diff = Date.now() - new Date(iso).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  return `${Math.floor(hrs / 24)}d ago`;
}

function RelativeTime({ iso }: { iso: string | null }) {
  const [time, setTime] = useState(() => formatRelativeTime(iso));

  useEffect(() => {
    const timer = setInterval(() => {
      setTime(formatRelativeTime(iso));
    }, 60000);
    return () => clearInterval(timer);
  }, [iso]);

  return <span>{time}</span>;
}

export function NotificationBell() {
  const { notifications, unreadCount, markAllRead, isPolling } = useNotifications();
  const [open, setOpen] = useState(false);
  const panelRef = useRef<HTMLDivElement>(null);

  // Close panel on outside click
  useEffect(() => {
    if (!open) return;
    function handleClick(e: MouseEvent) {
      if (panelRef.current && !panelRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, [open]);

  function handleToggle() {
    setOpen((v) => !v);
    if (!open) markAllRead();
  }

  return (
    <div className="notif-bell" ref={panelRef} style={{ position: "relative" }}>
      {/* Bell Button */}
      <button
        className="notif-bell__btn"
        onClick={handleToggle}
        title="Email Notifications"
        style={{
          position: "relative",
          background: "none",
          border: "1px solid var(--border)",
          borderRadius: "var(--radius-sm)",
          padding: "6px 8px",
          cursor: "pointer",
          color: "var(--text-secondary)",
          display: "flex",
          alignItems: "center",
          gap: 6,
          transition: "all 0.2s ease",
        }}
      >
        {/* Bell SVG */}
        <svg
          width="16"
          height="16"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
          style={{
            color: unreadCount > 0 ? "var(--text-accent, #7c6af7)" : "inherit",
            animation: unreadCount > 0 ? "bellRing 0.6s ease 0s 1" : "none",
          }}
        >
          <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9" />
          <path d="M13.73 21a2 2 0 0 1-3.46 0" />
        </svg>

        {/* Polling pulse dot */}
        {isPolling && (
          <span
            style={{
              width: 5,
              height: 5,
              borderRadius: "50%",
              background: "#22c55e",
              display: "inline-block",
              animation: "pulse 1s ease infinite",
            }}
          />
        )}

        {/* Unread badge */}
        {unreadCount > 0 && (
          <span
            style={{
              position: "absolute",
              top: -5,
              right: -5,
              minWidth: 18,
              height: 18,
              borderRadius: 99,
              background: "#ef4444",
              color: "#fff",
              fontSize: 10,
              fontWeight: 700,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              padding: "0 4px",
              boxShadow: "0 0 0 2px var(--bg-base)",
              animation: "badgePop 0.3s cubic-bezier(0.34,1.56,0.64,1)",
            }}
          >
            {unreadCount > 9 ? "9+" : unreadCount}
          </span>
        )}
      </button>

      {/* Dropdown Panel */}
      {open && (
        <div
          style={{
            position: "absolute",
            top: "calc(100% + 8px)",
            right: 0,
            width: 340,
            background: "var(--bg-card)",
            border: "1px solid var(--border)",
            borderRadius: "var(--radius)",
            boxShadow: "0 8px 32px rgba(0,0,0,0.35)",
            zIndex: 9999,
            overflow: "hidden",
            animation: "slideDown 0.18s ease",
          }}
        >
          {/* Header */}
          <div
            style={{
              padding: "12px 16px",
              borderBottom: "1px solid var(--border)",
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
            }}
          >
            <div>
              <div style={{ fontWeight: 700, fontSize: 13 }}>📬 HR Email Alerts</div>
              <div style={{ fontSize: 11, color: "var(--text-muted)", marginTop: 2 }}>
                Auto-synced every 30 seconds
              </div>
            </div>
            {isPolling && (
              <span style={{ fontSize: 10, color: "#22c55e", fontWeight: 600 }}>
                ● LIVE
              </span>
            )}
          </div>

          {/* Notification list */}
          <div style={{ maxHeight: 360, overflowY: "auto" }}>
            {notifications.length === 0 ? (
              <div
                style={{
                  padding: 24,
                  textAlign: "center",
                  color: "var(--text-muted)",
                  fontSize: 13,
                }}
              >
                <div style={{ fontSize: 28, marginBottom: 8 }}>📭</div>
                No HR responses yet
              </div>
            ) : (
              notifications.map((n, i) => (
                <div
                  key={n.id}
                  style={{
                    padding: "12px 16px",
                    borderBottom:
                      i < notifications.length - 1
                        ? "1px solid var(--border)"
                        : "none",
                    background: "transparent",
                    transition: "background 0.15s",
                  }}
                  onMouseEnter={(e) =>
                    ((e.currentTarget as HTMLDivElement).style.background =
                      "var(--bg-surface)")
                  }
                  onMouseLeave={(e) =>
                    ((e.currentTarget as HTMLDivElement).style.background =
                      "transparent")
                  }
                >
                  <div
                    style={{
                      display: "flex",
                      justifyContent: "space-between",
                      marginBottom: 4,
                    }}
                  >
                    <span
                      style={{
                        fontSize: 11,
                        fontWeight: 600,
                        color: "var(--text-accent, #7c6af7)",
                        textTransform: "uppercase",
                        letterSpacing: "0.05em",
                      }}
                    >
                      {n.company_name}
                    </span>
                    <span style={{ fontSize: 10, color: "var(--text-muted)" }}>
                      <RelativeTime iso={n.timestamp} />
                    </span>
                  </div>
                  <div
                    style={{
                      fontSize: 12,
                      fontWeight: 600,
                      marginBottom: 4,
                      color: "var(--text-primary)",
                    }}
                  >
                    {n.subject}
                  </div>
                  <div
                    style={{
                      fontSize: 11,
                      color: "var(--text-muted)",
                      lineHeight: 1.5,
                    }}
                  >
                    {n.snippet}
                  </div>
                </div>
              ))
            )}
          </div>

          {/* Footer */}
          <div
            style={{
              padding: "10px 16px",
              borderTop: "1px solid var(--border)",
              fontSize: 11,
              color: "var(--text-muted)",
              textAlign: "center",
            }}
          >
            Go to Drive Workspace → Email Thread to read full emails
          </div>
        </div>
      )}
    </div>
  );
}
