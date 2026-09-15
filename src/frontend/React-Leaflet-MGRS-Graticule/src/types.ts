export interface LatLngPoint {
  lat: number;
  lng: number;
  lon?: number; // Some internal functions use lon instead of lng
}

export interface UtmPoint {
  easting: number;
  northing: number;
  zoneNumber: number;
  zoneLetter: string;
}

export interface GraticuleOptions {
  showGrid?: boolean;
  color?: string;
  font?: string;
  fontColor?: string;
  dashArray?: number[];
  weight?: number;
  gridColor?: string;
  hkColor?: string;
  hkDashArray?: number[];
  gridFont?: string;
  gridFontColor?: string;
  gridDashArray?: number[];
  hundredKMinZoom?: number;
  tenKMinZoom?: number;
  oneKMinZoom?: number;
  hundredMMinZoom?: number;
  minZoom?: number;
}

export interface MgrsGraticuleProps {
  name: string;
  checked: boolean;
  options?: GraticuleOptions;
}