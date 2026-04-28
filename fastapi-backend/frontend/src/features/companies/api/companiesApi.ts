import type { Company, EmailLog } from "../../../shared/types/api";
import { requestData } from "../../../shared/lib/api";

export interface CompanyPayload {
  company_name: string;
  email: string;
  priority?: string | null;
  description?: string | null;
  poc_name?: string | null;
  poc_phone?: string | null;
  poc_email?: string | null;
  alternate_poc_name?: string | null;
  alternate_poc_phone?: string | null;
  alternate_poc_email?: string | null;
  location?: string | null;
  address?: string | null;
}

export const companiesApi = {
  list() {
    return requestData<Company[]>("/company/all");
  },
  create(payload: CompanyPayload) {
    return requestData<Company>("/company/create", {
      method: "POST",
      body: JSON.stringify(payload),
    });
  },
  update(id: number, payload: Partial<CompanyPayload>) {
    return requestData<Company>(`/company/${id}`, {
      method: "PUT",
      body: JSON.stringify(payload),
    });
  },
  remove(id: number) {
    return requestData<null>(`/company/${id}`, {
      method: "DELETE",
    });
  },
  getEmails(id: number) {
    return requestData<EmailLog[]>(`/company/${id}/emails`);
  },
};
