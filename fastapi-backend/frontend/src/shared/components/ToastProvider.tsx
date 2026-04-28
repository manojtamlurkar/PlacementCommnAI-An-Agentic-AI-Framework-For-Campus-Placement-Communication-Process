import { createContext, useContext, useState, useCallback, type ReactNode } from "react";

interface Toast { id: number; message: string; type: "success" | "error" | "info"; }
interface ToastCtx { pushToast: (message: string, type?: Toast["type"]) => void; }

const Ctx = createContext<ToastCtx>({ pushToast: () => {} });
export const useToast = () => useContext(Ctx);

let _id = 0;

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);

  const pushToast = useCallback((message: string, type: Toast["type"] = "success") => {
    const id = ++_id;
    setToasts((prev) => [...prev, { id, message, type }]);
    setTimeout(() => setToasts((prev) => prev.filter((t) => t.id !== id)), 4000);
  }, []);

  return (
    <Ctx.Provider value={{ pushToast }}>
      {children}
      <div className="toast-stack">
        {toasts.map((t) => (
          <div key={t.id} className={`toast toast--${t.type}`}>
            <span className="toast__dot" />
            {t.message}
          </div>
        ))}
      </div>
    </Ctx.Provider>
  );
}
