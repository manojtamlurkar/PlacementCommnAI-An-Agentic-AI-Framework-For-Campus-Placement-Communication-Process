export interface StandardResponse<T> {
  success: boolean;
  message: string;
  data: T | null;
}

export interface Company {
  id: number;
  company_name: string;
  email: string;
  priority: string | null;
  description: string | null;
  poc_name: string | null;
  poc_phone: string | null;
  poc_email: string | null;
  alternate_poc_name: string | null;
  alternate_poc_phone: string | null;
  alternate_poc_email: string | null;
  location: string | null;
  address: string | null;
  created_at: string;
  updated_at: string;
}

export interface RecruitmentDrive {
  id: number;
  company_name: string;
  hr_email: string;
  status: string;
  spoc_name: string | null;
  spoc_email: string | null;
}

export interface Approval {
  id: number;
  recruitment_id: number;
  action: string;
  status: string;
  payload: string | null;
}

export interface ActivityLog {
  id: number;
  drive_id: number | null;
  company_id: number | null;
  actor: string;
  action: string;
  details: string;
  timestamp: string;
}

export interface TelegramGroup {
  id: number;
  company_id: number;
  drive_id: number | null;
  chat_id: string;
  group_name: string;
  invite_link: string | null;
  is_active: boolean;
  created_at: string;
}

export interface StudentQuestion {
  id: number;
  company_id: number;
  drive_id: number | null;
  telegram_user: string;
  question_text: string;
  status: string;
  auto_answer: string | null;
  hr_answer: string | null;
  created_at: string;
  answered_at: string | null;
}

export interface EmailLog {
  id: number;
  company_id: number;
  direction: string;
  subject: string;
  body: string;
  timestamp: string;
}

export interface ParsedEmail {
  sender: string;
  subject: string;
  snippet: string;
  llm_insight?: string;
}

export interface Classroom {
  id: number;
  name: string;
  building: string | null;
  capacity: number;
  has_projector: boolean;
  created_at: string;
}

export interface LogisticsEntry {
  id: number;
  company_id: number;
  classroom_id: number | null;
  drive_date: string;
  student_count: number;
  status: string;
  registration_link: string | null;
  followup_questions: string | null;
  created_at: string;
  updated_at: string;
}

export interface NextStepInfo {
  current_status: string;
  next_action: string | null;
}

export interface DriveWorkspaceViewModel {
  drive: RecruitmentDrive;
  company: Company | null;
  nextStep: NextStepInfo | null;
  emails: EmailLog[];
  activity: ActivityLog[];
  telegramGroup: TelegramGroup | null;
  questions: StudentQuestion[];
}
