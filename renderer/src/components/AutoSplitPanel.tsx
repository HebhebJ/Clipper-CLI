import React, { useState } from 'react';

type Preset = 'original' | 'tiktok-9-16';
type TextAlignH = 'left' | 'center' | 'right';
type TextAlignV = 'top' | 'middle' | 'bottom';

interface Props {
    inputPath: string | null;
    outputDir: string;
    onBusyChange?: (busy: boolean) => void;
    appendLog: (msg: string) => void;
    clearLog: () => void;
}

export const AutoSplitPanel: React.FC<Props> = ({
    inputPath,
    outputDir,
    onBusyChange,
    appendLog,
    clearLog,
}) => {
    const [chunkSeconds, setChunkSeconds] = useState(30);
    const [busy, setBusy] = useState(false);

    const [preset, setPreset] = useState<Preset>('original');
    const [labelPrefix, setLabelPrefix] = useState(''); // blank by default

    const [alignH, setAlignH] = useState<TextAlignH>('center');
    const [alignV, setAlignV] = useState<TextAlignV>('bottom');
    const [fontSize, setFontSize] = useState(48);
    const [fontColor, setFontColor] = useState('#ffffff');
    const [box, setBox] = useState(true);

    const handleSplit = async () => {
        if (!inputPath) {
            alert('Please select an input video first.');
            return;
        }
        if (!chunkSeconds || chunkSeconds <= 0) {
            alert('Chunk length must be > 0.');
            return;
        }

        clearLog();
        appendLog(
            `Starting auto split into "${outputDir}" with preset=${preset}...\n`
        );

        setBusy(true);
        onBusyChange?.(true);

        try {
            const res = await window.clipperApi.autoSplit({
                inputPath,
                outputDir,
                chunkSeconds,
                preset,
                labelPrefix: labelPrefix.trim() || undefined,
                textStyle:
                    labelPrefix.trim().length > 0
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
            }
        } catch (err: any) {
            appendLog(`\n❌ Exception: ${err.message}`);
        } finally {
            setBusy(false);
            onBusyChange?.(false);
        }
    };

    return (
        <div className="card">
            <h2>Auto Split into Equal Chunks</h2>
            <p className="hint">Output: {outputDir}</p>

            <label className="label">Aspect preset</label>
            <select
                value={preset}
                onChange={(e) => setPreset(e.target.value as Preset)}
            >
                <option value="original">Original</option>
                <option value="tiktok-9-16">TikTok Vertical (9:16)</option>
            </select>

            <label className="label">
                Overlay label prefix (optional, e.g. &quot;Part&quot;)
            </label>
            <input
                type="text"
                value={labelPrefix}
                onChange={(e) => setLabelPrefix(e.target.value)}
                placeholder='Example: "Part" → Part 1, Part 2...'
            />

            {labelPrefix.trim().length > 0 && (
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

            <label className="label">Chunk length (seconds)</label>
            <input
                type="number"
                value={chunkSeconds}
                min={1}
                onChange={(e) => setChunkSeconds(Number(e.target.value))}
            />

            <button onClick={handleSplit} disabled={busy || !inputPath}>
                Split video into chunks
            </button>
        </div>
    );
};
