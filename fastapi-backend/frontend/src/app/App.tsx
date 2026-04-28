import { AppShell } from "./AppShell";
import { ToastProvider } from "../shared/components/ToastProvider";
import { NotificationProvider } from "../shared/components/NotificationProvider";

export function App() {
  return (
    <ToastProvider>
      <NotificationProvider>
        <AppShell />
      </NotificationProvider>
    </ToastProvider>
  );
}
