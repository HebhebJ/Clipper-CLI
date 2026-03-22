import React, { useState } from 'react';

type Preset = 'original' | 'tiktok-9-16';
type TextAlignH = 'left' | 'center' | 'right';
type TextAlignV = 'top' | 'middle' | 'bottom';

interface Props {
    inputPath: string | null;
    playhead: number;
    outputDir: string;
    appendLog: (msg: string) => void;
}

export const ManualClipPanel: React.FC<Props> = ({
    inputPath,
    playhead,
    outputDir,
    appendLog,
}) => {
    const [start, setStart] = useState<number | ''>('');
    const [end, setEnd] = useState<number | ''>('');
    const [outputName, setOutputName] = useState('highlight_1.mp4');
    const [busy, setBusy] = useState(false);

    const [preset, setPreset] = useState<Preset>('original');
    const [labelText, setLabelText] = useState('');

    const [alignH, setAlignH] = useState<TextAlignH>('center');
    const [alignV, setAlignV] = useState<TextAlignV>('bottom');
    const [fontSize, setFontSize] = useState(48);
    const [fontColor, setFontColor] = useState('#ffffff');
    const [box, setBox] = useState(true);
    const [generateSubs, setGenerateSubs] = useState(false);
    const [burnSubs, setBurnSubs] = useState(false);

    const setStartFromPlayhead = () => {
        const t = Number(playhead.toFixed(3));
        setStart(t);
    };

    const setEndFromPlayhead = () => {
        const t = Number(playhead.toFixed(3));
        setEnd(t);
    };

    const handleExport = async () => {
        if (!inputPath) {
            alert('Select a video first.');
            return;
        }
        if (start === '' || end === '') {
            alert('Set start and end times.');
            return;
        }
        if (end <= start) {
            alert('End must be > start.');
            return;
        }

        const name = outputName || 'clip.mp4';
        const sep = outputDir.includes('\\') ? '\\' : '/';
        const outputPath = outputDir + sep + name;

        appendLog(
            `\n[UI] Exporting single clip...\nstart=${start}s end=${end}s\noutput=${outputPath}\n`
        );

        setBusy(true);
        try {
            const res = await window.clipperApi.cutClip({
                inputPath,
                outputPath,
                startSeconds: start,
                endSeconds: end,
                preset,
                labelText: labelText.trim() || undefined,
                textStyle:
                    labelText.trim().length > 0
                        ? {
                            alignH,
                            alignV,
                            fontSize,
                            fontColor,
                            box,
                        }
                        : undefined,
            });

            if (!res.ok) {
                appendLog(`\n❌ Failed: ${res.error ?? 'Unknown error'}`);
            } else {
                // 👉 add this block here
                const clipPath = outputPath;
                let srtPath: string | undefined;

                if (generateSubs) {
                    appendLog('\n[UI] Generating subtitles (whisper)...');
                    const resSubs = await window.clipperApi.generateSubtitles({
                        clipPath,
                    });
                    if (!resSubs.ok || !resSubs.srtPath) {
                        appendLog(
                            `\n❌ Subtitles failed: ${resSubs.error ?? 'Unknown error'}`
                        );
                    } else {
                        srtPath = resSubs.srtPath;
                        appendLog(`\n[UI] Subtitles ready: ${srtPath}`);
                    }
                }

                if (burnSubs && srtPath) {
                    const subbedPath = outputPath.replace(
                        /\.mp4$/i,
                        '_subbed.mp4'
                    );
                    appendLog(
                        `\n[UI] Burning subtitles into video:\n${subbedPath}`
                    );
                    const resBurn = await window.clipperApi.burnSubtitles({
                        clipPath,
                        srtPath,
                        outputPath: subbedPath,
                    });
                    if (!resBurn.ok) {
                        appendLog(
                            `\n❌ Burn subtitles failed: ${resBurn.error ?? 'Unknown error'
                            }`
                        );
                    } else {
                        appendLog(`\n[UI] Subbed clip: ${resBurn.outputPath}`);
                    }
                }
            }

        } catch (err: any) {
            appendLog(`\n❌ Exception: ${err.message}`);
        } finally {
            setBusy(false);
        }
    };

    return (
        <div className="card">
            <h2>Manual Clip</h2>
            <p className="hint">
                Move the video playhead to a moment, then click “Set start” / “Set end”.
            </p>

            <div className="row" style={{ gap: 8 }}>
                <div style={{ flex: 1 }}>
                    <label className="label">Start (seconds)</label>
                    <input
                        type="number"
                        value={start}
                        onChange={(e) => setStart(Number(e.target.value))}
                    />
                    <button
                        onClick={setStartFromPlayhead}
                        disabled={!inputPath || busy}
                        style={{ marginTop: 8 }}
                    >
                        Set start from video
                    </button>
                </div>

                <div style={{ flex: 1 }}>
                    <label className="label">End (seconds)</label>
                    <input
                        type="number"
                        value={end}
                        onChange={(e) => setEnd(Number(e.target.value))}
                    />
                    <button
                        onClick={setEndFromPlayhead}
                        disabled={!inputPath || busy}
                        style={{ marginTop: 8 }}
                    >
                        Set end from video
                    </button>
                </div>
            </div>

            <label className="label">Output file name</label>
            <input
                type="text"
                value={outputName}
                onChange={(e) => setOutputName(e.target.value)}
            />

            <label className="label">Aspect preset</label>
            <select
                value={preset}
                onChange={(e) => setPreset(e.target.value as Preset)}
            >
                <option value="original">Original</option>
                <option value="tiktok-9-16">TikTok Vertical (9:16)</option>
            </select>

            <label className="label">Overlay text (optional)</label>
            <input
                type="text"
                value={labelText}
                onChange={(e) => setLabelText(e.target.value)}
                placeholder='e.g. "Part 3 – OT comeback"'
            />

            {labelText.trim().length > 0 && (
                <>
                    <label className="label">Text position</label>
                    <div className="row" style={{ gap: 8 }}>
                        <select
                            value={alignH}
                            onChange={(e) =>
                                setAlignH(e.target.value as TextAlignH)
                            }
                        >
                            <option value="left">Left</option>
                            <option value="center">Center</option>
                            <option value="right">Right</option>
                        </select>
                        <select
                            value={alignV}
                            onChange={(e) =>
                                setAlignV(e.target.value as TextAlignV)
                            }
                        >
                            <option value="top">Top</option>
                            <option value="middle">Middle</option>
                            <option value="bottom">Bottom</option>
                        </select>
                    </div>

                    <label className="label">Font size</label>
                    <input
                        type="number"
                        min={10}
                        max={200}
                        value={fontSize}
                        onChange={(e) => setFontSize(Number(e.target.value))}
                    />

                    <label className="label">Font color</label>
                    <input
                        type="color"
                        value={fontColor}
                        onChange={(e) => setFontColor(e.target.value)}
                    />

                    <label className="label" style={{ display: 'flex', gap: 8 }}>
                        <input
                            type="checkbox"
                            checked={box}
                            onChange={(e) => setBox(e.target.checked)}
                        />
                        Box background
                    </label>
                </>
            )}
            <label className="label" style={{ display: 'flex', gap: 8 }}>
                <input
                    type="checkbox"
                    checked={generateSubs}
                    onChange={(e) => setGenerateSubs(e.target.checked)}
                />
                Generate subtitles (SRT)
            </label>

            <label className="label" style={{ display: 'flex', gap: 8 }}>
                <input
                    type="checkbox"
                    checked={burnSubs}
                    onChange={(e) => setBurnSubs(e.target.checked)}
                    disabled={!generateSubs}
                />
                Burn subtitles into new video
            </label>

            <button
                onClick={handleExport}
                disabled={busy || !inputPath}
                style={{ marginTop: 12 }}
            >
                Export single clip
            </button>
        </div>
    );
};
