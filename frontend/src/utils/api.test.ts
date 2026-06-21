import { afterEach, describe, expect, it, vi } from 'vitest';
import { apiUrl, downloadUrl, fetchTaskStatus } from './api';

describe('api client', () => {
    afterEach(() => {
        vi.restoreAllMocks();
    });

    it('builds backend URLs for relative paths', () => {
        expect(apiUrl('/api/health')).toBe('http://127.0.0.1:17654/api/health');
        expect(apiUrl('api/health')).toBe('http://127.0.0.1:17654/api/health');
        expect(apiUrl('https://example.test/x')).toBe('https://example.test/x');
    });

    it('normalizes optional download URLs', () => {
        expect(downloadUrl(undefined)).toBeNull();
        expect(downloadUrl('/api/files/download?path=x')).toBe(
            'http://127.0.0.1:17654/api/files/download?path=x',
        );
    });

    it('fetches task status and propagates payloads', async () => {
        vi.spyOn(globalThis, 'fetch').mockResolvedValue({
            ok: true,
            json: async () => ({
                task_id: 'abc',
                status: 'success',
                task_type: 'ocr',
                input_path: 'in.pdf',
                output_path: 'out.pdf',
                progress: 100,
            }),
        } as Response);

        await expect(fetchTaskStatus('abc')).resolves.toMatchObject({
            task_id: 'abc',
            status: 'success',
            progress: 100,
        });
    });
});
