import type { MAP_STYLES } from "../components/map/MapConfig";

export type MapStyleKey = keyof typeof MAP_STYLES;

export type MapStyleSwitcherProps = {
  currentStyle: MapStyleKey;
  onStyleChange: (style: MapStyleKey) => void;
  showMgrsGrid: boolean;
  onMgrsToggle: (enabled: boolean) => void;
};
