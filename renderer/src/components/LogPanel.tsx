// renderer/src/components/LogPanel.tsx
import React from 'react';

interface Props {
    log: string;
}

export const LogPanel: React.FC<Props> = ({ log }) => {
    return (
        <div className="card">
            <h2>Logs</h2>
            <div className="log-box">{log}</div>
        </div>
    );
};
