import { tg } from "./telegram";

export type Role = "admin" | "teacher" | "student";
export type BlockType = "text" | "gif" | "image" | "video";

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
}
export interface LessonShort {
  id: number;
  title: string;
  position: number;
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
  blocks: Block[];
  prev_lesson_id: number | null;
  next_lesson_id: number | null;
}

export interface Material {
  id: number;
  title: string;
  filename: string;
  kind: "pdf" | "docx" | "text";
  status: "parsed";
  char_count: number;
  module_id: number | null;
  chunk_count: number;
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
  users: () => request<User[]>("GET", "/users"),
  setRole: (userId: number, role: Role) => request<User>("PATCH", `/users/${userId}/role`, { role }),

  modules: () => request<Module[]>("GET", "/modules"),
  module: (id: number) => request<ModuleDetail>("GET", `/modules/${id}`),
  createModule: (data: { title: string; description: string; position: number }) =>
    request<Module>("POST", "/modules", data),
  deleteModule: (id: number) => request<void>("DELETE", `/modules/${id}`),

  lesson: (id: number) => request<LessonDetail>("GET", `/lessons/${id}`),
  createLesson: (moduleId: number, data: { title: string; position: number }) =>
    request<LessonShort>("POST", `/modules/${moduleId}/lessons`, data),
  deleteLesson: (id: number) => request<void>("DELETE", `/lessons/${id}`),

  createBlock: (lessonId: number, data: Omit<Block, "id">) => request<Block>("POST", `/lessons/${lessonId}/blocks`, data),
  deleteBlock: (id: number) => request<void>("DELETE", `/blocks/${id}`),

  materials: () => request<Material[]>("GET", "/materials"),
  material: (id: number) => request<MaterialDetail>("GET", `/materials/${id}`),
  uploadMaterial: (file: File, title: string, moduleId: number | null) => {
    const form = new FormData();
    form.append("file", file);
    form.append("title", title);
    if (moduleId !== null) form.append("module_id", String(moduleId));
    return request<Material>("POST", "/materials", form);
  },
  deleteMaterial: (id: number) => request<void>("DELETE", `/materials/${id}`),
};
