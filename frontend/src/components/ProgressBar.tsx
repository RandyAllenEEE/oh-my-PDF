import React, { useEffect, useState } from 'react';

interface ProgressBarProps {
    wsUrl?: string;
}

export const ProgressBar: React.FC<ProgressBarProps> = ({ wsUrl = "ws://localhost:8000/ws/progress" }) => {
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
    }, [wsUrl]);

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
