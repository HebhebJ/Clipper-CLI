export { };

type TextAlignH = 'left' | 'center' | 'right';
type TextAlignV = 'top' | 'middle' | 'bottom';

interface TextStylePayload {
    alignH?: TextAlignH;
    alignV?: TextAlignV;
    fontSize?: number;
    fontColor?: string;
    box?: boolean;
}

declare global {
    interface ClipperApi {
        openFile: () => Promise<string | null>;
        selectOutputDir: () => Promise<string | null>;
        autoSplit: (options: {
            inputPath: string;
            outputDir: string;
            chunkSeconds: number;
            preset?: 'original' | 'tiktok-9-16';
            labelPrefix?: string;
            textStyle?: TextStylePayload; // 👈
        }) => Promise<{ ok: boolean; error?: string }>;
        cutClip: (options: {
            inputPath: string;
            outputPath: string;
            startSeconds: number;
            endSeconds: number;
            preset?: 'original' | 'tiktok-9-16';
            labelText?: string;
            textStyle?: TextStylePayload; // 👈
        }) => Promise<{ ok: boolean; error?: string }>;
        onLog: (cb: (message: string) => void) => void;
        generateSubtitles: (options: {
            clipPath: string;
        }) => Promise<{ ok: boolean; srtPath?: string; error?: string }>;
        burnSubtitles: (options: {
            clipPath: string;
            srtPath: string;
            outputPath: string;
        }) => Promise<{ ok: boolean; outputPath?: string; error?: string }>;
    }

    interface Window {
        clipperApi: ClipperApi;
    }
}
