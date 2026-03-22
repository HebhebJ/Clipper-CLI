const fs = require('fs');
const path = require('path');
const { spawn } = require('child_process');

// Helper to run ffmpeg as a Promise
function runFfmpeg(args) {
    return new Promise((resolve, reject) => {
        console.log('\n[ffmpeg]', args.join(' '));

        const ff = spawn('ffmpeg', args, { stdio: ['ignore', 'pipe', 'pipe'] });

        ff.stdout.on('data', (data) => {
            // Usually ffmpeg logs to stderr, but just in case
            // console.log('[ffmpeg stdout]', data.toString());
        });

        ff.stderr.on('data', (data) => {
            const text = data.toString();
            process.stdout.write(text);
        });

        ff.on('close', (code) => {
            if (code === 0) {
                resolve();
            } else {
                reject(new Error(`ffmpeg exited with code ${code}`));
            }
        });
    });
}

// Helper to get video duration in seconds using ffprobe
function getVideoDuration(inputPath) {
    return new Promise((resolve, reject) => {
        const args = [
            '-v',
            'error',
            '-show_entries',
            'format=duration',
            '-of',
            'default=noprint_wrappers=1:nokey=1',
            inputPath,
        ];

        const fp = spawn('ffprobe', args, { stdio: ['ignore', 'pipe', 'pipe'] });

        let output = '';
        let errorOutput = '';

        fp.stdout.on('data', (data) => {
            output += data.toString();
        });

        fp.stderr.on('data', (data) => {
            errorOutput += data.toString();
        });

        fp.on('close', (code) => {
            if (code !== 0) {
                return reject(
                    new Error(
                        `ffprobe exited with code ${code}. stderr: ${errorOutput}`
                    )
                );
            }
            const duration = parseFloat(output.trim());
            if (Number.isNaN(duration)) {
                return reject(new Error('Could not parse ffprobe duration output'));
            }
            resolve(duration);
        });
    });
}

// Load config file passed as first argument
function loadConfig() {
    const configPath = process.argv[2];

    if (!configPath) {
        console.error('Usage: node clipper.js path/to/project.json');
        process.exit(1);
    }

    const fullPath = path.resolve(configPath);
    if (!fs.existsSync(fullPath)) {
        console.error(`Config file not found: ${fullPath}`);
        process.exit(1);
    }

    const raw = fs.readFileSync(fullPath, 'utf-8');
    return JSON.parse(raw);
}

// Build ffmpeg args for one clip
function buildFfmpegArgs({ input, outputPath, start, end, duration }) {
    const args = [];

    // Fast seek (put -ss before -i). For more precise cuts, move -ss after -i.
    if (start !== undefined) {
        args.push('-ss', String(start));
    }

    args.push('-i', input);

    if (end !== undefined) {
        args.push('-to', String(end));
    } else if (duration !== undefined) {
        args.push('-t', String(duration));
    }

    // -c copy = no re-encode (super fast when possible)
    args.push('-c', 'copy');

    args.push(outputPath);

    return args;
}

// Generate auto-split clips if no manual clips defined
async function generateAutoSplitClips(config, inputPath) {
    const auto = config.autoSplit;
    if (!auto) return [];

    const mode = auto.mode || 'duration';

    if (mode !== 'duration') {
        console.warn(
            `autoSplit.mode "${mode}" not supported yet. Supported: "duration".`
        );
        return [];
    }

    const chunkSeconds = Number(auto.chunkSeconds || 30);
    if (!chunkSeconds || chunkSeconds <= 0) {
        console.warn('autoSplit.chunkSeconds must be a positive number.');
        return [];
    }

    console.log('\n[autoSplit] Getting video duration via ffprobe...');
    const duration = await getVideoDuration(inputPath);
    console.log(`[autoSplit] Video duration: ${duration.toFixed(2)} seconds`);

    const totalChunks = Math.ceil(duration / chunkSeconds);
    console.log(
        `[autoSplit] Splitting into ${totalChunks} chunk(s) of ~${chunkSeconds}s`
    );

    const prefix = auto.prefix || 'clip_';
    const ext = auto.extension || 'mp4';

    const clips = [];

    for (let i = 0; i < totalChunks; i++) {
        const start = i * chunkSeconds;
        const remaining = duration - start;
        const thisDuration = Math.min(remaining, chunkSeconds);

        const name = `${prefix}${i + 1}.${ext}`;

        clips.push({
            name,
            start,
            duration: thisDuration,
        });
    }

    return clips;
}

async function main() {
    const config = loadConfig();

    const input = path.resolve(config.input);
    const outputDir = path.resolve(config.outputDir || 'output_clips');

    if (!fs.existsSync(input)) {
        console.error(`Input file not found: ${input}`);
        process.exit(1);
    }

    if (!fs.existsSync(outputDir)) {
        fs.mkdirSync(outputDir, { recursive: true });
    }

    // Start from manual clips if provided; clone to avoid mutating config directly
    let clips = Array.isArray(config.clips) ? [...config.clips] : [];

    // If no manual clips and autoSplit is configured, generate automatic chunks
    if (clips.length === 0 && config.autoSplit) {
        try {
            const autoClips = await generateAutoSplitClips(config, input);
            clips = autoClips;
        } catch (err) {
            console.error('Error during autoSplit:', err.message);
            process.exit(1);
        }
    }

    if (clips.length === 0) {
        console.error('No clips defined (manual or autoSplit).');
        process.exit(1);
    }

    console.log(`Input: ${input}`);
    console.log(`Output dir: ${outputDir}`);
    console.log(`Number of clips: ${clips.length}`);

    for (const [index, clip] of clips.entries()) {
        const name = clip.name || `clip_${index + 1}.mp4`;
        const outputPath = path.join(outputDir, name);

        const start = clip.start;
        const end = clip.end;
        const duration = clip.duration;

        if (start === undefined) {
            console.error(`Clip ${name} is missing "start"`);
            continue;
        }

        if (end === undefined && duration === undefined) {
            console.error(`Clip ${name} needs either "end" or "duration"`);
            continue;
        }

        console.log(`\n=== Processing clip ${index + 1}/${clips.length}: ${name} ===`);

        const args = buildFfmpegArgs({
            input,
            outputPath,
            start,
            end,
            duration,
        });

        try {
            await runFfmpeg(args);
            console.log(`\n✅ Done: ${outputPath}`);
        } catch (err) {
            console.error(`\n❌ Error processing ${name}:`, err.message);
        }
    }

    console.log('\nAll clips processed.');
}

main().catch((err) => {
    console.error('Fatal error:', err);
    process.exit(1);
});
