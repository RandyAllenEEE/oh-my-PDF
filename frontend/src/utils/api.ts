export interface UploadedPdf {
    status: 'success';
    filename: string;
    path: string;
    size: number;
}

export interface TaskStatus {
    task_id: string;
    status: 'pending' | 'running' | 'success' | 'failed';
    task_type: string;
    input_path: string;
    output_path: string;
    progress: number;
    error_message?: string | null;
    download_url?: string;
}

const viteApiBase = import.meta.env.VITE_API_BASE_URL as string | undefined;
const isBrowser = typeof window !== 'undefined';
const DEFAULT_API_BASE_URL = 'http://127.0.0.1:17654';

export const API_BASE_URL = viteApiBase || (isBrowser ? window.location.origin : DEFAULT_API_BASE_URL);

export const WS_BASE_URL = API_BASE_URL.replace(/^http/, 'ws');

export const apiUrl = (path: string): string => {
    if (/^https?:\/\//.test(path)) return path;
    return `${API_BASE_URL}${path.startsWith('/') ? path : `/${path}`}`;
};

export const downloadUrl = (path?: string): string | null => {
    if (!path) return null;
    return apiUrl(path);
};

export async function uploadPdf(file: File): Promise<UploadedPdf> {
    const body = new FormData();
    body.append('file', file);

    const response = await fetch(apiUrl('/api/files/upload'), {
        method: 'POST',
        body,
    });

    if (!response.ok) {
        const detail = await readError(response);
        throw new Error(detail || `Upload failed (${response.status})`);
    }

    return response.json();
}

export async function fetchTaskStatus(taskId: string): Promise<TaskStatus> {
    const response = await fetch(apiUrl(`/api/tasks/${taskId}`));
    if (!response.ok) {
        const detail = await readError(response);
        throw new Error(detail || `Task status failed (${response.status})`);
    }
    return response.json();
}

export async function waitForTask(
    taskId: string,
    onUpdate?: (task: TaskStatus) => void,
    intervalMs = 1000,
): Promise<TaskStatus> {
    while (true) {
        const task = await fetchTaskStatus(taskId);
        onUpdate?.(task);

        if (task.status === 'success') return task;
        if (task.status === 'failed') {
            throw new Error(task.error_message || 'Task failed');
        }

        await new Promise(resolve => window.setTimeout(resolve, intervalMs));
    }
}

async function readError(response: Response): Promise<string | null> {
    try {
        const data = await response.json();
        return data.detail || data.message || null;
    } catch {
        return response.statusText || null;
    }
}
