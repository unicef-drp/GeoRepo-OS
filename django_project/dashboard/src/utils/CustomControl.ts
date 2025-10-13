import React from "react";
import { createRoot, Root } from "react-dom/client";
import maplibregl from "maplibre-gl";


class CustomControl {
  protected map: maplibregl.Map;
  private container: HTMLDivElement;
  private root: Root;

  onRender(): React.ReactNode {
    return null
  }

  className(): string {
    return null
  }

  onAdd(map: maplibregl.Map) {
    this.map = map;

    // Create a container for the control
    this.container = document.createElement('div');
    this.container.className = this.className();
    this.root = createRoot(this.container);
    this.root.render(this.onRender());
    return this.container;
  }

  onRemove() {
    this.root.unmount();
    this.container.parentNode.removeChild(this.container);
    this.map = undefined;
  }
}

export default CustomControl;
