// core/videoService.js
const fs = require('fs');
const path = require('path');
const { runFfmpeg, getVideoDuration } = require('./ffmpegRunner');

// Build -vf filter graph string depending on preset + text
function buildVideoFilters({ preset, labelText, textStyle }) {
    const filters = [];

    // TikTok vertical 9:16: scale height to 1920, crop width to 1080 (centered)
    if (preset === 'tiktok-9-16') {
        filters.push('scale=-2:1920');
        filters.push('crop=1080:1920:(in_w-1080)/2:0');
    }

    if (labelText && labelText.trim().length > 0) {
        const safeText = labelText.replace(/:/g, '\\:').replace(/'/g, "\\'");

        // ----- defaults -----
        const alignH = textStyle?.alignH || 'center'; // 'left' | 'center' | 'right'
        const alignV = textStyle?.alignV || 'bottom'; // 'top' | 'middle' | 'bottom'
        const fontSize = textStyle?.fontSize || 64;
        const fontColor = textStyle?.fontColor || 'white';
        const box = textStyle?.box ?? true;

        // compute x
        let xExpr;
        if (alignH === 'left') xExpr = '50';
        else if (alignH === 'right') xExpr = 'w-text_w-50';
        else xExpr = '(w-text_w)/2';

        // compute y
        let yExpr;
        if (alignV === 'top') yExpr = '100';
        else if (alignV === 'middle') yExpr = '(h-text_h)/2';
        else yExpr = 'h-text_h-150';

        // explicit font file on Windows to avoid fontconfig issues
        let fontFile = null;
        if (process.platform === 'win32') {
            const windir = process.env.WINDIR || 'C:\\Windows';
            fontFile = (windir + '\\Fonts\\arial.ttf').replace(/\\/g, '/');
        }

        const parts = [
            'drawtext=',
            "text='" + safeText + "'",
            `:x=${xExpr}`,
            `:y=${yExpr}`,
            `:fontsize=${fontSize}`,
            `:fontcolor=${fontColor}`,
        ];

        if (box) {
            parts.push(':bordercolor=black');
            parts.push(':borderw=4');
            parts.push(':box=1');
            parts.push(':boxcolor=black@0.4');
            parts.push(':boxborderw=15');
        }

        if (fontFile) {
            const safeFont = fontFile.replace(/:/g, '\\:').replace(/'/g, "\\'");
            parts.push(`:fontfile='${safeFont}'`);
        }

        filters.push(parts.join(''));
    }

    if (filters.length === 0) return null;
    return filters.join(',');
}



// Build ffmpeg args depending on preset + label
function buildFfmpegArgsWithPreset({
    input,
    outputPath,
    start,
    duration,
    preset = 'original',
    labelText,
    textStyle,
}) {
    const args = [];

    args.push('-ss', String(start));
    args.push('-i', input);
    args.push('-t', String(duration));

    const filterGraph = buildVideoFilters({ preset, labelText, textStyle });

    if (!filterGraph) {
        // No filters → copy for speed
        args.push('-c', 'copy');
    } else {
        args.push('-vf', filterGraph);
        args.push('-c:v', 'libx264');
        args.push('-preset', 'veryfast');
        args.push('-crf', '18');
        // args.push('-c:a', 'copy');
        // Re-encode audio to a standard AAC track to avoid "silent" issues
        args.push('-c:a', 'aac');
        args.push('-b:a', '160k');
    }

    args.push(outputPath);
    return args;
}


/**
 * Auto-split one video into equal chunks.
 *
 * @param {Object} options
 * @param {string} options.inputPath
 * @param {string} options.outputDir
 * @param {number} options.chunkSeconds
 * @param {'original' | 'tiktok-9-16'} [options.preset]
 * @param {string} [options.labelPrefix]
 * @param {(log: string) => void} [options.onLog]
 */
async function autoSplitVideo({
    inputPath,
    outputDir,
    chunkSeconds,
    preset = 'original',
    labelPrefix,
    textStyle,       // 👈 NEW
    onLog,
}) {
    const input = path.resolve(inputPath);
    const outDir = path.resolve(outputDir);

    if (!fs.existsSync(input)) {
        throw new Error(`Input file not found: ${input}`);
    }
    if (!fs.existsSync(outDir)) {
        fs.mkdirSync(outDir, { recursive: true });
    }
    if (!chunkSeconds || chunkSeconds <= 0) {
        throw new Error('chunkSeconds must be a positive number.');
    }

    if (onLog) onLog('[autoSplit] Probing video duration...');
    const duration = await getVideoDuration(input);
    if (onLog)
        onLog(`[autoSplit] Video duration: ${duration.toFixed(2)} seconds`);

    const totalChunks = Math.ceil(duration / chunkSeconds);
    if (onLog)
        onLog(
            `[autoSplit] Splitting into ${totalChunks} chunk(s) of ~${chunkSeconds}s`
        );

    for (let i = 0; i < totalChunks; i++) {
        const start = i * chunkSeconds;
        const remaining = duration - start;
        const thisDuration = Math.min(remaining, chunkSeconds);

        const index = i + 1;
        const name = `chunk_${index}.mp4`;
        const outputPath = path.join(outDir, name);

        const labelText =
            labelPrefix && labelPrefix.trim().length > 0
                ? `${labelPrefix} ${index}`
                : undefined;

        if (onLog)
            onLog(
                `\n[autoSplit] Chunk ${index}/${totalChunks}: start=${start.toFixed(
                    2
                )}s, duration=${thisDuration.toFixed(
                    2
                )}s, file=${name}, preset=${preset}, label=${labelText || 'none'
                }`
            );

        const args = buildFfmpegArgsWithPreset({
            input,
            outputPath,
            start,
            duration: thisDuration,
            preset,
            textStyle, // 👈 pass it through
            labelText,
        });

        await runFfmpeg(args, onLog);
    }

    if (onLog) onLog('\n[autoSplit] All chunks done.');
}

/**
 * Cut a single clip.
 *
 * @param {Object} options
 * @param {string} options.inputPath
 * @param {string} options.outputPath
 * @param {number} options.startSeconds
 * @param {number} options.endSeconds
 * @param {'original' | 'tiktok-9-16'} [options.preset]
 * @param {string} [options.labelText]
 * @param {(log: string) => void} [options.onLog]
 */
async function cutSingleClip({
    inputPath,
    outputPath,
    startSeconds,
    endSeconds,
    preset = 'original',
    labelText,
    textStyle,        // 👈 NEW
    onLog,
}) {
    const input = path.resolve(inputPath);
    const out = path.resolve(outputPath);

    if (!fs.existsSync(input)) {
        throw new Error(`Input file not found: ${input}`);
    }
    if (startSeconds < 0 || endSeconds <= startSeconds) {
        throw new Error('Invalid start/end times.');
    }

    const duration = endSeconds - startSeconds;

    if (onLog)
        onLog(
            `\n[cut] Cutting clip...\nstart=${startSeconds.toFixed(
                2
            )}s, end=${endSeconds.toFixed(
                2
            )}s, duration=${duration.toFixed(
                2
            )}s, preset=${preset}, label=${labelText || 'none'}\n`
        );

    const args = buildFfmpegArgsWithPreset({
        input,
        outputPath: out,
        start: startSeconds,
        duration,
        preset,
        labelText,
        textStyle, // 👈 pass it through
    });

    await runFfmpeg(args, onLog);
    if (onLog) onLog(`\n[cut] Done: ${out}`);
}

module.exports = {
    autoSplitVideo,
    cutSingleClip,
};
