// core/ffmpegRunner.js
const { spawn } = require('child_process');


function runFfmpeg(args, onLog, { overwrite = true } = {}) {
    return new Promise((resolve, reject) => {
        const finalArgs = overwrite ? ['-y', ...args] : ['-n', ...args];

        if (onLog) onLog('[ffmpeg] ' + finalArgs.join(' '));

        const ff = spawn('ffmpeg', finalArgs);

        ff.stdout.on('data', (data) => {
            const text = data.toString();
            if (onLog) onLog(text);
        });

        ff.stderr.on('data', (data) => {
            const text = data.toString();
            if (onLog) onLog(text);
        });

        ff.on('close', (code) => {
            if (code === 0) resolve();
            else reject(new Error(`ffmpeg exited with code ${code}`));
        });
    });
}



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

        const fp = spawn('ffprobe', args);

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

module.exports = {
    runFfmpeg,
    getVideoDuration,
};
