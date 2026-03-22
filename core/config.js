// core/config.js
const path = require('path');

const defaultWhisperExe =
    process.platform === 'win32'
        ? 'C:\\whisper\\whisper.cpp\\build\\bin\\whisper-cli.exe'
        : '/usr/local/bin/whisper-cli';

const defaultWhisperModel =
    process.platform === 'win32'
        ? 'C:\\whisper\\whisper.cpp\\models\\ggml-base.en.bin'
        : '/opt/whisper/models/ggml-base.en.bin';

module.exports = {
    // Override with WHISPER_EXE in your shell/.env.
    whisperExe: process.env.WHISPER_EXE || defaultWhisperExe,
    // Override with WHISPER_MODEL in your shell/.env.
    whisperModel: process.env.WHISPER_MODEL || defaultWhisperModel,

    resolve(p) {
        return path.resolve(__dirname, '..', p);
    },
};
