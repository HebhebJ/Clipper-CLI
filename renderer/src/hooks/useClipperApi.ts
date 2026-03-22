// renderer/src/hooks/useClipperApi.ts
import { useEffect, useState, useCallback } from 'react';

export function useClipperApi() {
    const [log, setLog] = useState('');

    useEffect(() => {
        if (!window.clipperApi) return;
        window.clipperApi.onLog((message) => {
            setLog((prev) => prev + message);
        });
    }, []);

    const appendLog = useCallback((msg: string) => {
        setLog((prev) => prev + msg);
    }, []);

    const clearLog = useCallback(() => {
        setLog('');
    }, []);

    return {
        log,
        appendLog,
        clearLog,
        clipperApi: window.clipperApi,
    };
}
