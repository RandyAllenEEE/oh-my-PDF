import React, { useEffect, useState } from 'react';
import { fetchTaskStatus, WS_BASE_URL, type TaskStatus } from '../utils/api';

interface ProgressBarProps {
    wsUrl?: string;
    taskId?: string | null;
    onComplete?: (task: TaskStatus) => void;
    onError?: (message: string) => void;
}

export const ProgressBar: React.FC<ProgressBarProps> = ({
    wsUrl = `${WS_BASE_URL}/ws/progress`,
    taskId,
    onComplete,
    onError,
}) => {
    const [messages, setMessages] = useState<string[]>([]);
    const [progress, setProgress] = useState(0);

    useEffect(() => {
        const ws = new WebSocket(wsUrl);

        ws.onopen = () => {
            console.log('Connected to WebSocket');
            setMessages(p => [...p, "Connected to server..."]);
        };

        ws.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                // Expecting format: { type: 'progress', value: 50, message: 'Processing page 1...' }
                if (data.type === 'progress') {
                    setProgress(data.value);
                    setMessages(p => [...p, data.message]);
                } else if (data.type === 'task_complete' && (!taskId || data.task_id === taskId)) {
                    setProgress(current => data.status === 'success' ? 100 : current);
                    setMessages(p => [...p, data.status === 'success' ? 'Task completed.' : `Task failed: ${data.error || 'Unknown error'}`]);
                }
            } catch (e) {
                console.log("Received raw text:", event.data);
            }
        };

        ws.onclose = () => {
            console.log('Disconnected from WebSocket');
        };

        return () => {
            ws.close();
        };
    }, [wsUrl, taskId]);

    useEffect(() => {
        if (!taskId) return;

        let cancelled = false;
        const poll = async () => {
            try {
                const task = await fetchTaskStatus(taskId);
                if (cancelled) return;

                setProgress(task.progress || (task.status === 'success' ? 100 : 10));
                setMessages(p => {
                    const latest = `Task ${task.status}${task.progress ? ` (${task.progress}%)` : ''}`;
                    return p[p.length - 1] === latest ? p : [...p, latest];
                });

                if (task.status === 'success') {
                    onComplete?.(task);
                    return;
                }
                if (task.status === 'failed') {
                    onError?.(task.error_message || 'Task failed');
                    return;
                }

                window.setTimeout(poll, 1000);
            } catch (error) {
                if (!cancelled) {
                    onError?.(`${error}`);
                }
            }
        };

        poll();

        return () => {
            cancelled = true;
        };
    }, [taskId, onComplete, onError]);

    return (
        <div className="w-full mt-4">
            <div className="w-full bg-gray-200 rounded-full h-2.5 dark:bg-gray-700">
                <div
                    className="bg-blue-600 h-2.5 rounded-full transition-all duration-300"
                    style={{ width: `${progress}%` }}
                ></div>
            </div>
            <div className="mt-2 text-xs text-gray-600 h-24 overflow-y-auto border p-2 rounded bg-gray-50 font-mono">
                {messages.map((msg, i) => (
                    <div key={i}>{msg}</div>
                ))}
                {messages.length === 0 && <span className="text-gray-400">Waiting for task...</span>}
            </div>
        </div>
    );
};
