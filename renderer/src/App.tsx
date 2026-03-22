// renderer/src/App.tsx
import React, { useState } from 'react';
import { useClipperApi } from './hooks/useClipperApi';
import { VideoPreview } from './components/VideoPreview';
import { AutoSplitPanel } from './components/AutoSplitPanel';
import { ManualClipPanel } from './components/ManualClipPanel';
import { LogPanel } from './components/LogPanel';

const App: React.FC = () => {
  const [inputPath, setInputPath] = useState<string | null>(null);
  const [outputDir, setOutputDir] = useState<string>('./output_clips'); // 👈 global
  const [playhead, setPlayhead] = useState(0);

  const { log, appendLog, clearLog } = useClipperApi();

  const handleSelectOutputDir = async () => {
    const dir = await window.clipperApi.selectOutputDir();
    if (dir) setOutputDir(dir);
  };

  return (
    <div className="app">
      <h1>Clipper – React Edition</h1>

      {/* GLOBAL OUTPUT SECTION */}
      <div className="card" style={{ marginBottom: 16 }}>
        <h2>Global Output Folder</h2>
        <div className="row">
          <input
            type="text"
            value={outputDir}
            readOnly
            style={{ flex: 1 }}
          />
          <button onClick={handleSelectOutputDir}>
            Change…
          </button>
        </div>
        <p className="hint">
          All exports (auto split + manual clips) will go into this folder.
        </p>
      </div>

      <div className="grid">
        <div>
          <VideoPreview
            inputPath={inputPath}
            onInputPathChange={setInputPath}
            onPlayheadChange={setPlayhead}
          />
          <ManualClipPanel
            inputPath={inputPath}
            playhead={playhead}
            outputDir={outputDir}   // 👈 use global
            appendLog={appendLog}
          />
        </div>
        <div>
          <AutoSplitPanel
            inputPath={inputPath}
            outputDir={outputDir}   // 👈 use global
            onBusyChange={() => { }}
            appendLog={appendLog}
            clearLog={clearLog}
          />
          <LogPanel log={log} />
        </div>
      </div>
    </div>
  );
};


export default App;
