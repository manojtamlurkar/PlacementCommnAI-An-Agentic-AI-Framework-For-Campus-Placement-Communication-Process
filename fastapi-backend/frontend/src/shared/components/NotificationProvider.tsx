import {
  createContext,
  useContext,
  useState,
  useEffect,
  useCallback,
  useRef,
  type ReactNode,
} from "react";
import { request } from "../lib/api";

export interface EmailNotification {
  id: number;
  company_name: string;
  subject: string;
  snippet: string;
  timestamp: string | null;
}

interface NotificationCtx {
  notifications: EmailNotification[];
  unreadCount: number;
  markAllRead: () => void;
  isPolling: boolean;
}

const Ctx = createContext<NotificationCtx>({
  notifications: [],
  unreadCount: 0,
  markAllRead: () => {},
  isPolling: false,
});

export const useNotifications = () => useContext(Ctx);

const POLL_INTERVAL_MS = 30_000; // poll every 30 seconds

export function NotificationProvider({ children }: { children: ReactNode }) {
  const [notifications, setNotifications] = useState<EmailNotification[]>([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const [isPolling, setIsPolling] = useState(false);

  // Track the highest email id we've seen so we can detect new ones
  const highestSeenId = useRef<number | null>(null);
  // Track ids that came in after app load (truly "new" in this session)
  const sessionStartId = useRef<number | null>(null);
  const initialized = useRef(false);

  const fetchNotifications = useCallback(async () => {
    setIsPolling(true);
    try {
      const url =
        highestSeenId.current !== null
          ? `/emails/notifications?since_id=${highestSeenId.current}`
          : `/emails/notifications`;

      const res = await request<{
        success: boolean;
        data: EmailNotification[];
        latest_id: number | null;
      }>(url);

      const incoming = res.data ?? [];

      if (!initialized.current) {
        // First load: record baseline — these are NOT "new" alerts for this session
        if (incoming.length > 0) {
          highestSeenId.current = incoming[0].id;
          sessionStartId.current = incoming[0].id;
        }
        initialized.current = true;
        // Show last 5 in the panel as context but mark them read
        setNotifications(incoming.slice(0, 5));
        setUnreadCount(0);
      } else if (incoming.length > 0) {
        // Subsequent polls: these are genuinely NEW emails
        highestSeenId.current = incoming[0].id;
        setNotifications((prev) => {
          const merged = [...incoming, ...prev];
          const seen = new Set<number>();
          return merged.filter((n) => {
            if (seen.has(n.id)) return false;
            seen.add(n.id);
            return true;
          });
        });
        setUnreadCount((prev) => prev + incoming.length);
      }
    } catch {
      // silently ignore polling errors
    } finally {
      setIsPolling(false);
    }
  }, []);

  // Initial fetch then poll
  useEffect(() => {
    void fetchNotifications();
    const timer = setInterval(() => void fetchNotifications(), POLL_INTERVAL_MS);
    return () => clearInterval(timer);
  }, [fetchNotifications]);

  const markAllRead = useCallback(() => {
    setUnreadCount(0);
  }, []);

  return (
    <Ctx.Provider value={{ notifications, unreadCount, markAllRead, isPolling }}>
      {children}
    </Ctx.Provider>
  );
}
