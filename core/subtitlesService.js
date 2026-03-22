// core/subtitlesService.js
const path = require('path');
const fs = require('fs');
const { spawn } = require('child_process');
const { runFfmpeg } = require('./ffmpegRunner');
const { whisperExe, whisperModel } = require('./config');

async function extractWav({ inputVideo, onLog }) {
    const input = path.resolve(inputVideo);
    const wavPath = input + '.whisper.wav';

    const args = [
        '-y', // overwrite
        '-i',
        input,
        '-ar',
        '16000',
        '-ac',
        '1',
        '-c:a',
        'pcm_s16le',
        wavPath,
    ];

    onLog && onLog(`\n[subs] Extracting WAV for whisper: ${wavPath}`);
    await runFfmpeg(args, onLog);
    return wavPath;
}

async function generateSubtitles({ inputVideo, onLog }) {
    const input = path.resolve(inputVideo);

    if (!fs.existsSync(input)) {
        throw new Error(`Video not found for subtitles: ${input}`);
    }
    if (!fs.existsSync(whisperExe)) {
        throw new Error(`Whisper executable not found: ${whisperExe}`);
    }
    if (!fs.existsSync(whisperModel)) {
        throw new Error(`Whisper model not found: ${whisperModel}`);
    }

    const wavPath = await extractWav({ inputVideo: input, onLog });

    const args = [
        '-np',
        '-f',
        wavPath,
        '-m',
        whisperModel,
        '-l',
        'auto',
        '-osrt',
    ];

    onLog &&
        onLog(`\n[subs] Running whisper:\n${whisperExe} ${args.join(' ')}\n`);

    const rawSrtPath = wavPath + '.srt';

    await new Promise((resolve, reject) => {
        const proc = spawn(whisperExe, args);

        proc.stdout.on('data', (data) => {
            onLog && onLog('[subs] ' + data.toString());
        });

        proc.stderr.on('data', (data) => {
            onLog && onLog('[subs] ' + data.toString());
        });

        proc.on('close', (code) => {
            if (code === 0) {
                resolve();
            } else {
                reject(new Error(`whisper exited with code ${code}`));
            }
        });
    });

    if (!fs.existsSync(rawSrtPath)) {
        throw new Error(`Whisper did not produce SRT: ${rawSrtPath}`);
    }

    const targetSrt = input.replace(/\.(mp4|mov|mkv|avi)$/i, '') + '.srt';
    fs.copyFileSync(rawSrtPath, targetSrt);

    try {
        fs.unlinkSync(wavPath);
        fs.unlinkSync(rawSrtPath);
    } catch (_) { }

    onLog && onLog(`\n[subs] Subtitles generated: ${targetSrt}\n`);
    return targetSrt;
}

async function burnSubtitles({ inputVideo, srtPath, outputVideo, onLog }) {
    const input = path.resolve(inputVideo);
    const srt = path.resolve(srtPath);
    const output = path.resolve(outputVideo);

    if (!fs.existsSync(input)) {
        throw new Error(`Video not found: ${input}`);
    }
    if (!fs.existsSync(srt)) {
        throw new Error(`SRT not found: ${srt}`);
    }

    const srtFilterPath = srt
        .replace(/\\/g, '/')
        .replace(/:/g, '\\:');

    const filter = `subtitles='${srtFilterPath}'`;

    const args = [
  '-y',
  '-i',
  input,
  '-vf',
  filter,
  '-c:v',
  'libx264',
  '-preset',
  'veryfast',
  '-crf',
  '18',
  '-c:a',
  'aac',
  '-b:a',
  '160k',
  output,
];


    onLog &&
        onLog(
            `\n[subs] Burning subtitles:\nffmpeg ${args.join(' ')}\n`
        );

    await runFfmpeg(args, onLog);
    onLog && onLog(`\n[subs] Subbed video written to: ${output}\n`);
    return output;
}

module.exports = {
    generateSubtitles,
    burnSubtitles,
};
