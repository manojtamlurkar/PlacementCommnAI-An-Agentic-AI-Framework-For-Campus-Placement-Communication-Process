import type { TelegramGroup } from "../../../shared/types/api";
import { request, requestData } from "../../../shared/lib/api";
import type { StandardResponse } from "../../../shared/types/api";

export const telegramApi = {
  getGroup(driveId: number) {
    return requestData<TelegramGroup>(`/telegram/group/${driveId}`);
  },
  createGroup(driveId: number) {
    return requestData<TelegramGroup>(`/telegram/create-group/${driveId}`, {
      method: "POST",
    });
  },
  draftBroadcast(driveId: number) {
    return requestData<{ draft: string }>(`/telegram/draft-broadcast/${driveId}`, {
      method: "POST",
    });
  },
  broadcastInvite(payload: {
    invite_link: string;
    company_name: string;
    custom_message?: string;
  }) {
    return request<StandardResponse<{ invite_link: string }>>(
      "/telegram/broadcast-invite",
      {
        method: "POST",
        body: JSON.stringify(payload),
      },
    );
  },
};
