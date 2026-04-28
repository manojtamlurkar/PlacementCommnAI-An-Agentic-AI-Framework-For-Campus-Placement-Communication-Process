import type { StudentQuestion } from "../../../shared/types/api";
import { request, requestData } from "../../../shared/lib/api";

export const spocApi = {
  listQuestions(driveId: number) {
    return requestData<StudentQuestion[]>(`/spoc/${driveId}/questions`);
  },
  forwardToHr(driveId: number, questionIds: number[]) {
    return request(`/spoc/${driveId}/forward-to-hr`, {
      method: "POST",
      body: JSON.stringify({ question_ids: questionIds }),
    });
  },
  answerQuestion(driveId: number, questionId: number, answer: string) {
    return request(`/spoc/${driveId}/answer-question/${questionId}`, {
      method: "POST",
      body: JSON.stringify({ answer }),
    });
  },
};
