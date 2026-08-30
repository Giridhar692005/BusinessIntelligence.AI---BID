import {
  Mosaic,
  MosaicWindow
} from "react-mosaic-component";

import AnomalyWindow from "./AnomalyWindow";
import PlotWindow from "./PlotWindow";
import AllKPIWindow from "./AllKPIWindow";
import RootCauseWindow from "./RootCauseWindow";

export default function Workspace({
  windows,
  layout,
  setLayout,
  file
}) {

  function renderWindow(id) {

    const window = windows.find(
      (w) => w.id === id
    );

    if (!window) return null;

    switch (window.type) {

      case "anomaly":
        return <AnomalyWindow file={file} />;

      case "plot":
        return <PlotWindow file={file} />;

      case "all":
        return <AllKPIWindow file={file} />;

      case "root":
        return <RootCauseWindow file={file} />;

      default:
        return null;
    }
  }


  function getTitle(id) {

    const window = windows.find(
      (w) => w.id === id
    );

    return window?.title || "Window";
  }


  return (

    <div className="workspace">

      <Mosaic
        value={layout}
        onChange={setLayout}

        renderTile={(id) => (

          <MosaicWindow
            path={id}
            title={getTitle(id)}
          >

            {renderWindow(id)}

          </MosaicWindow>

        )}

      />

    </div>
  );
}