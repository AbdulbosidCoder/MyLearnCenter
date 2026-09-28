import { tg } from "./telegram";

export type Role = "admin" | "teacher" | "student";
export type BlockType = "text" | "gif" | "image" | "video" | "viz";
export type RewriteMode = "simpler" | "example" | "shorter" | "custom";

export interface User {
  id: number;
  telegram_id: number;
  first_name: string;
  username: string | null;
  role: Role;
}
export interface Module {
  id: number;
  title: string;
  description: string;
  position: number;
  lesson_count: number;
  draft_count: number;
}
/** done: test passed; locked: an earlier lesson's test is not passed yet. */
export type LessonState = "done" | "open" | "locked";
export interface LessonShort {
  id: number;
  title: string;
  position: number;
  level: number;
  is_draft: boolean;
  state: LessonState;
  has_test: boolean;
}
export interface ModuleDetail extends Module {
  lessons: LessonShort[];
}
export interface Block {
  id: number;
  type: BlockType;
  content: string;
  caption: string;
  position: number;
}
export interface LessonDetail {
  id: number;
  module_id: number;
  module_title: string;
  title: string;
  position: number;
  level: number;
  is_draft: boolean;
  question_count: number;
  blocks: Block[];
  prev_lesson_id: number | null;
  next_lesson_id: number | null;
  state: LessonState;
  next_unlocked: boolean;
}

export interface Material {
  id: number;
  title: string;
  filename: string;
  kind: "pdf" | "docx" | "text" | "image";
  status: "parsed" | "generating" | "draft_ready" | "failed";
  char_count: number;
  chunks_done: number;
  error: string;
  module_id: number | null;
  chunk_count: number;
  /** Reading the pictures and filling the knowledge base, after the upload. */
  index_status: "pending" | "ready" | "failed";
  images_done: number;
  image_count: number;
}
export interface MaterialImage {
  id: number;
  number: number;
  url: string;
  caption: string;
  ocr_text: string;
}
export interface MaterialChunk {
  id: number;
  position: number;
  heading: string;
  text: string;
  char_count: number;
}
export interface MaterialDetail extends Material {
  chunks: MaterialChunk[];
  images: MaterialImage[];
}
export interface AiStatus {
  claude: boolean;
  ocr_languages: string;
  captions: boolean;
  embeddings: boolean;
}
export interface AskResult {
  answer: string;
  image_text: string;
  sources: { title: string; image_url: string | null }[];
}

export interface Question {
  id: number;
  position: number;
  kind: "single" | "multiple";
  prompt: string;
  options: string[];
  // Only teachers and the admin receive the answers before submitting.
  correct?: number[];
  explanation?: string;
}
export interface Quiz {
  lesson_id: number;
  pass_score: number;
  questions: Question[];
}
export interface QuizResult {
  correct_count: number;
  total: number;
  passed: boolean;
  results: { question_id: number; is_correct: boolean; correct: number[]; explanation: string }[];
  module_id: number;
  next_lesson_id: number | null;
}

export interface Quest {
  key: "xp" | "test" | "perfect";
  title: string;
  value: number;
  goal: number;
}
export interface Stats {
  xp_total: number;
  xp_today: number;
  streak: number;
  tests_passed: number;
  quests: Quest[];
}
export interface RatingRow {
  place: number;
  name: string;
  xp: number;
  is_me: boolean;
}
export interface Leaderboard {
  rows: RatingRow[];
  me: RatingRow | null;
  total: number;
}

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
  }
}

function authHeaders(): Record<string, string> {
  if (tg?.initData) return { Authorization: `tma ${tg.initData}` };
  const devUser = import.meta.env.VITE_DEV_USER;
  return devUser ? { "X-Dev-User": String(devUser) } : {};
}

async function request<T>(method: string, path: string, body?: unknown): Promise<T> {
  // FormData (file upload) sets its own multipart Content-Type.
  const isForm = body instanceof FormData;
  const res = await fetch(`/api${path}`, {
    method,
    headers: isForm ? authHeaders() : { "Content-Type": "application/json", ...authHeaders() },
    body: body === undefined ? undefined : isForm ? body : JSON.stringify(body),
  });
  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    throw new ApiError(res.status, typeof data.detail === "string" ? data.detail : res.statusText);
  }
  return res.status === 204 ? (undefined as T) : res.json();
}

export const api = {
  me: () => request<User>("GET", "/me"),
  stats: () => request<Stats>("GET", "/me/stats"),
  leaderboard: () => request<Leaderboard>("GET", "/leaderboard"),
  path: () => request<ModuleDetail[]>("GET", "/path"),
  users: () => request<User[]>("GET", "/users"),
  setRole: (userId: number, role: Role) => request<User>("PATCH", `/users/${userId}/role`, { role }),

  modules: () => request<Module[]>("GET", "/modules"),
  module: (id: number) => request<ModuleDetail>("GET", `/modules/${id}`),
  createModule: (data: { title: string; description: string; position: number }) =>
    request<Module>("POST", "/modules", data),
  publishModule: (id: number) => request<Module>("POST", `/modules/${id}/publish`),
  deleteModule: (id: number) => request<void>("DELETE", `/modules/${id}`),

  lesson: (id: number) => request<LessonDetail>("GET", `/lessons/${id}`),
  createLesson: (moduleId: number, data: { title: string; position: number }) =>
    request<LessonShort>("POST", `/modules/${moduleId}/lessons`, data),
  deleteLesson: (id: number) => request<void>("DELETE", `/lessons/${id}`),

  createBlock: (lessonId: number, data: Omit<Block, "id">) => request<Block>("POST", `/lessons/${lessonId}/blocks`, data),
  updateBlock: (id: number, data: Partial<Omit<Block, "id">>) => request<Block>("PATCH", `/blocks/${id}`, data),
  rewriteBlock: (id: number, mode: RewriteMode, instruction = "") =>
    request<{ text: string }>("POST", `/blocks/${id}/rewrite`, { mode, instruction }),
  widgets: () => request<{ name: string; title: string; params: Record<string, unknown> }[]>("GET", "/widgets"),
  deleteBlock: (id: number) => request<void>("DELETE", `/blocks/${id}`),

  quiz: (lessonId: number) => request<Quiz>("GET", `/lessons/${lessonId}/quiz`),
  submitQuiz: (lessonId: number, answers: Record<number, number[]>) =>
    request<QuizResult>("POST", `/lessons/${lessonId}/quiz`, { answers }),
  deleteQuestion: (id: number) => request<void>("DELETE", `/questions/${id}`),

  materials: () => request<Material[]>("GET", "/materials"),
  material: (id: number) => request<MaterialDetail>("GET", `/materials/${id}`),
  uploadMaterial: (file: File, title: string, moduleId: number | null) => {
    const form = new FormData();
    form.append("file", file);
    form.append("title", title);
    if (moduleId !== null) form.append("module_id", String(moduleId));
    return request<Material>("POST", "/materials", form);
  },
  generateLessons: (id: number) => request<Material>("POST", `/materials/${id}/generate`),
  reindexMaterial: (id: number) => request<Material>("POST", `/materials/${id}/index`),

  aiStatus: () => request<AiStatus>("GET", "/ai/status"),
  ask: (question: string, lessonId: number | null, image: File | null) => {
    const form = new FormData();
    form.append("question", question);
    if (lessonId !== null) form.append("lesson_id", String(lessonId));
    if (image) form.append("image", image);
    return request<AskResult>("POST", "/ai/ask", form);
  },
  deleteMaterial: (id: number) => request<void>("DELETE", `/materials/${id}`),
};
