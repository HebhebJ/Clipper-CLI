import React, { useEffect, useRef } from 'react';

interface Props {
    inputPath: string | null;
    onInputPathChange: (path: string | null) => void;
    onPlayheadChange: (time: number) => void; // 👈 new
}

function toFileUrl(p: string) {
    let pathWithForwardSlashes = p.replace(/\\/g, '/');
    if (!pathWithForwardSlashes.startsWith('/')) {
        pathWithForwardSlashes = '/' + pathWithForwardSlashes;
    }
    return 'file://' + encodeURI(pathWithForwardSlashes);
}

export const VideoPreview: React.FC<Props> = ({
    inputPath,
    onInputPathChange,
    onPlayheadChange,
}) => {
    const videoRef = useRef<HTMLVideoElement | null>(null);

    const handleBrowse = async () => {
        const file = await window.clipperApi.openFile();
        if (file) {
            onInputPathChange(file);
        }
    };

    // when inputPath changes, update video src
    useEffect(() => {
        if (!videoRef.current) return;
        if (!inputPath) {
            videoRef.current.removeAttribute('src');
            return;
        }
        videoRef.current.src = toFileUrl(inputPath);
        videoRef.current.load();
    }, [inputPath]);

    // report time updates upward
    const handleTimeUpdate = () => {
        if (!videoRef.current) return;
        onPlayheadChange(videoRef.current.currentTime);
    };

    return (
        <div className="card">
            <h2>Video Preview</h2>
            <video
                ref={videoRef}
                controls
                style={{
                    width: '100%',
                    maxHeight: 360,
                    background: '#000',
                    borderRadius: 8,
                    marginBottom: 8,
                }}
                onTimeUpdate={handleTimeUpdate}    // 👈 key
            />
            <label className="label">Input video</label>
            <div className="row">
                <input
                    type="text"
                    value={inputPath ?? ''}
                    readOnly
                    placeholder="No file selected"
                />
                <button onClick={handleBrowse}>Browse…</button>
            </div>
        </div>
    );
};
