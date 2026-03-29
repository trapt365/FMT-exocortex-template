import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { z } from "zod";

const API_BASE = "https://api.singularity-app.com/v2";

function getToken(): string {
  const token = process.env.SINGULARITY_API_TOKEN;
  if (!token) {
    throw new Error(
      "SINGULARITY_API_TOKEN not set. Get it from me.singularity-app.com → «Доступ AI и API»"
    );
  }
  return token;
}

async function apiRequest<T>(
  path: string,
  params?: Record<string, string>,
  options?: { method?: string; body?: unknown }
): Promise<T> {
  const url = new URL(`${API_BASE}${path}`);
  if (params) {
    for (const [key, value] of Object.entries(params)) {
      if (value !== undefined && value !== "") {
        url.searchParams.set(key, value);
      }
    }
  }

  const method = options?.method ?? "GET";
  const response = await fetch(url.toString(), {
    method,
    headers: {
      Authorization: `Bearer ${getToken()}`,
      "Content-Type": "application/json",
    },
    body: options?.body !== undefined ? JSON.stringify(options.body) : undefined,
  });

  if (!response.ok) {
    const body = await response.text();
    throw new Error(`Singularity API ${response.status}: ${body}`);
  }

  // DELETE и PATCH могут вернуть пустой ответ
  const text = await response.text();
  if (!text) return {} as T;
  return JSON.parse(text) as T;
}

// --- Types ---

interface Task {
  id: string;
  title: string;
  note: string;
  priority: number; // 0=HIGH, 1=NORMAL, 2=LOW
  start: string;
  deadline: string;
  checked: number; // 0=EMPTY, 1=CHECKED, 2=CANCELLED
  projectId: string;
  parent: string;
  useTime: boolean;
  timeLength: number;
  tags: string[];
  deferred: boolean;
  scheduleOrder: number;
}

interface Project {
  id: string;
  title: string;
  note: string;
  emoji: string;
  parent: string;
  parentOrder: number;
  isNotebook: boolean;
  tags: string[];
}

interface TaskListResponse {
  tasks: Task[];
}

interface ProjectListResponse {
  projects: Project[];
}

// --- Formatters ---

const PRIORITY_LABELS: Record<number, string> = {
  0: "высокий",
  1: "обычный",
  2: "низкий",
};

const CHECK_LABELS: Record<number, string> = {
  0: "не выполнено",
  1: "выполнено",
  2: "отменено",
};

function formatTask(task: Task, projectName?: string): string {
  const parts: string[] = [];
  const priority = PRIORITY_LABELS[task.priority] ?? `${task.priority}`;
  const status = task.checked != null ? (CHECK_LABELS[task.checked] ?? `${task.checked}`) : "не выполнено";

  parts.push(`**${task.title}** (id: ${task.id})`);
  parts.push(`  Статус: ${status} | Приоритет: ${priority}`);

  if (projectName) parts.push(`  Проект: ${projectName}`);
  if (task.start) {
    const d = new Date(task.start);
    const time = d.toLocaleTimeString("ru-RU", { hour: "2-digit", minute: "2-digit", timeZone: "Asia/Almaty" });
    parts.push(`  Начало: ${time}`);
  }
  if (task.deadline) {
    const dl = new Date(task.deadline);
    parts.push(`  Дедлайн: ${dl.toLocaleDateString("ru-RU", { timeZone: "Asia/Almaty" })}`);
  }
  if (task.useTime && task.timeLength)
    parts.push(`  Длительность: ${task.timeLength} мин`);
  if (task.tags?.length) parts.push(`  Теги: ${task.tags.join(", ")}`);
  if (task.note) parts.push(`  Заметка: ${task.note.slice(0, 200)}`);

  return parts.join("\n");
}

// --- Server ---

const server = new McpServer({
  name: "singularity-mcp",
  version: "0.1.0",
});

// Cache projects for name resolution
let projectCache: Map<string, string> | null = null;

async function getProjectName(projectId: string): Promise<string> {
  if (!projectId) return "";
  if (!projectCache) {
    const data = await apiRequest<ProjectListResponse>("/project", {
      maxCount: "1000",
    });
    projectCache = new Map(data.projects.map((p) => [p.id, p.title]));
  }
  return projectCache.get(projectId) ?? projectId;
}

// Tool: list-tasks-today
server.tool(
  "list-tasks-today",
  "Список задач из SingularityApp на сегодня (по дате start). Возвращает задачи, запланированные на текущий день.",
  {},
  async () => {
    const today = new Date();
    const dateStr = today.toISOString().split("T")[0];
    // startDateFrom/To are inclusive, filter tasks for today
    const data = await apiRequest<TaskListResponse>("/task", {
      startDateFrom: `${dateStr}T00:00:00.000Z`,
      startDateTo: `${dateStr}T23:59:59.999Z`,
      maxCount: "200",
    });

    // Note: Singularity API v2 only returns active tasks (no includeCompleted param available)
    const active = data.tasks.filter((t) => !t.checked || t.checked === 0);
    // Sort by start time, then scheduleOrder
    active.sort((a, b) => {
      const ta = a.start ? new Date(a.start).getTime() : 0;
      const tb = b.start ? new Date(b.start).getTime() : 0;
      return ta - tb || a.scheduleOrder - b.scheduleOrder;
    });

    if (active.length === 0) {
      return {
        content: [
          { type: "text" as const, text: `Задач на ${dateStr} не найдено.` },
        ],
      };
    }

    // Resolve project names
    const lines: string[] = [`## Задачи на ${dateStr} (${active.length})\n`];
    for (const task of active) {
      const projName = await getProjectName(task.projectId);
      lines.push(formatTask(task, projName));
      lines.push("");
    }

    return {
      content: [{ type: "text" as const, text: lines.join("\n") }],
    };
  }
);

// Tool: list-projects
server.tool(
  "list-projects",
  "Список проектов из SingularityApp. Опционально фильтрует по подстроке в названии.",
  {
    filter: z
      .string()
      .optional()
      .describe("Подстрока для фильтрации по названию проекта"),
    includeArchived: z
      .boolean()
      .optional()
      .describe("Включить архивные проекты"),
  },
  async ({ filter, includeArchived }) => {
    const data = await apiRequest<ProjectListResponse>("/project", {
      maxCount: "1000",
      includeArchived: includeArchived ? "true" : "false",
    });

    let projects = data.projects.filter((p) => !p.isNotebook);
    if (filter) {
      const lower = filter.toLowerCase();
      projects = projects.filter((p) =>
        p.title.toLowerCase().includes(lower)
      );
    }

    // Build tree: group by parent
    const rootProjects = projects.filter((p) => !p.parent);
    const childMap = new Map<string, Project[]>();
    for (const p of projects) {
      if (p.parent) {
        const children = childMap.get(p.parent) ?? [];
        children.push(p);
        childMap.set(p.parent, children);
      }
    }

    const lines: string[] = [`## Проекты (${projects.length})\n`];
    for (const root of rootProjects) {
      const emoji = root.emoji ? `${root.emoji} ` : "";
      lines.push(`- ${emoji}**${root.title}**`);
      const children = childMap.get(root.id) ?? [];
      children.sort((a, b) => a.parentOrder - b.parentOrder);
      for (const child of children) {
        const ce = child.emoji ? `${child.emoji} ` : "";
        lines.push(`  - ${ce}${child.title}`);
      }
    }

    // Update project cache
    projectCache = new Map(data.projects.map((p) => [p.id, p.title]));

    return {
      content: [{ type: "text" as const, text: lines.join("\n") }],
    };
  }
);

// Tool: get-task
server.tool(
  "get-task",
  "Получить детали задачи по ID из SingularityApp.",
  {
    taskId: z.string().describe("ID задачи в SingularityApp"),
  },
  async ({ taskId }) => {
    const task = await apiRequest<Task>(`/task/${taskId}`);
    const projName = await getProjectName(task.projectId);
    const text = formatTask(task, projName);

    return {
      content: [{ type: "text" as const, text }],
    };
  }
);

// Tool: list-tasks
server.tool(
  "list-tasks",
  "Список задач из SingularityApp с фильтрами по проекту и дате.",
  {
    projectId: z
      .string()
      .optional()
      .describe("ID проекта для фильтрации"),
    startDateFrom: z
      .string()
      .optional()
      .describe("Начало диапазона дат (ISO 8601)"),
    startDateTo: z
      .string()
      .optional()
      .describe("Конец диапазона дат (ISO 8601)"),
    maxCount: z
      .number()
      .optional()
      .describe("Максимальное количество задач (до 1000)"),
  },
  async ({ projectId, startDateFrom, startDateTo, maxCount }) => {
    const params: Record<string, string> = {
      maxCount: String(maxCount ?? 200),
    };
    if (projectId) params.projectId = projectId;
    if (startDateFrom) params.startDateFrom = startDateFrom;
    if (startDateTo) params.startDateTo = startDateTo;

    // Note: Singularity API v2 only returns active tasks (no includeCompleted param available)
    const data = await apiRequest<TaskListResponse>("/task", params);

    const tasks = data.tasks.filter((t) => !t.checked || t.checked === 0);
    tasks.sort((a, b) => a.scheduleOrder - b.scheduleOrder);

    const lines: string[] = [`## Задачи (${tasks.length})\n`];
    for (const task of tasks) {
      const projName = await getProjectName(task.projectId);
      lines.push(formatTask(task, projName));
      lines.push("");
    }

    return {
      content: [{ type: "text" as const, text: lines.join("\n") }],
    };
  }
);

// Tool: create-task
server.tool(
  "create-task",
  "Создать задачу в SingularityApp.",
  {
    title: z.string().describe("Название задачи"),
    note: z.string().optional().describe("Заметка / описание"),
    projectId: z.string().optional().describe("ID проекта"),
    priority: z
      .enum(["high", "normal", "low"])
      .optional()
      .describe("Приоритет: high=0, normal=1, low=2"),
    startDate: z
      .string()
      .optional()
      .describe("Дата начала ISO 8601 (например 2026-03-24T10:00:00.000Z)"),
    deadline: z
      .string()
      .optional()
      .describe("Дедлайн ISO 8601"),
    tags: z
      .array(z.string())
      .optional()
      .describe("Список тегов"),
    useTime: z.boolean().optional().describe("Использовать временной слот"),
    timeLength: z.number().optional().describe("Длительность в минутах"),
  },
  async ({ title, note, projectId, priority, startDate, deadline, tags, useTime, timeLength }) => {
    const PRIORITY_MAP: Record<string, number> = { high: 0, normal: 1, low: 2 };
    const body: Record<string, unknown> = { title };
    if (note !== undefined) body.note = note;
    if (projectId !== undefined) body.projectId = projectId;
    if (priority !== undefined) body.priority = PRIORITY_MAP[priority];
    if (startDate !== undefined) body.start = startDate;
    if (deadline !== undefined) body.deadline = deadline;
    if (tags !== undefined) body.tags = tags;
    if (useTime !== undefined) body.useTime = useTime;
    if (timeLength !== undefined) body.timeLength = timeLength;

    const task = await apiRequest<Task>("/task", undefined, { method: "POST", body });
    const projName = await getProjectName(task.projectId);
    return {
      content: [
        {
          type: "text" as const,
          text: `✅ Задача создана (ID: ${task.id})\n\n${formatTask(task, projName)}`,
        },
      ],
    };
  }
);

// Tool: update-task
server.tool(
  "update-task",
  "Обновить поля задачи в SingularityApp (только переданные поля).",
  {
    taskId: z.string().describe("ID задачи"),
    title: z.string().optional().describe("Новое название"),
    note: z.string().optional().describe("Новая заметка"),
    projectId: z.string().optional().describe("Новый ID проекта"),
    priority: z
      .enum(["high", "normal", "low"])
      .optional()
      .describe("Приоритет: high=0, normal=1, low=2"),
    startDate: z.string().optional().describe("Новая дата начала ISO 8601"),
    deadline: z.string().optional().describe("Новый дедлайн ISO 8601"),
    tags: z.array(z.string()).optional().describe("Новый список тегов"),
    useTime: z.boolean().optional().describe("Использовать временной слот"),
    timeLength: z.number().optional().describe("Длительность в минутах"),
  },
  async ({ taskId, title, note, projectId, priority, startDate, deadline, tags, useTime, timeLength }) => {
    const PRIORITY_MAP: Record<string, number> = { high: 0, normal: 1, low: 2 };
    const body: Record<string, unknown> = {};
    if (title !== undefined) body.title = title;
    if (note !== undefined) body.note = note;
    if (projectId !== undefined) body.projectId = projectId;
    if (priority !== undefined) body.priority = PRIORITY_MAP[priority];
    if (startDate !== undefined) body.start = startDate;
    if (deadline !== undefined) body.deadline = deadline;
    if (tags !== undefined) body.tags = tags;
    if (useTime !== undefined) body.useTime = useTime;
    if (timeLength !== undefined) body.timeLength = timeLength;

    const task = await apiRequest<Task>(`/task/${taskId}`, undefined, { method: "PATCH", body });
    const projName = await getProjectName(task.projectId);
    return {
      content: [
        {
          type: "text" as const,
          text: `✅ Задача обновлена\n\n${formatTask(task, projName)}`,
        },
      ],
    };
  }
);

// Tool: complete-task
server.tool(
  "complete-task",
  "Отметить задачу как выполненную (checked=1) или отменённую (checked=2) в SingularityApp.",
  {
    taskId: z.string().describe("ID задачи"),
    action: z
      .enum(["complete", "cancel", "reopen"])
      .describe("complete=выполнено, cancel=отменено, reopen=переоткрыть"),
  },
  async ({ taskId, action }) => {
    const CHECKED_MAP: Record<string, number> = { complete: 1, cancel: 2, reopen: 0 };
    const body = { checked: CHECKED_MAP[action] };

    const task = await apiRequest<Task>(`/task/${taskId}`, undefined, { method: "PATCH", body });
    const projName = await getProjectName(task.projectId);
    const actionLabel: Record<string, string> = {
      complete: "выполнена",
      cancel: "отменена",
      reopen: "переоткрыта",
    };
    return {
      content: [
        {
          type: "text" as const,
          text: `✅ Задача ${actionLabel[action]}\n\n${formatTask(task, projName)}`,
        },
      ],
    };
  }
);

// --- Start ---

async function main() {
  const transport = new StdioServerTransport();
  await server.connect(transport);
}

main().catch((error) => {
  console.error("Failed to start singularity-mcp:", error);
  process.exit(1);
});
