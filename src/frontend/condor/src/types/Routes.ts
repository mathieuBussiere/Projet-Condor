export interface RouteFeature {
  type: "Feature";
  geometry: {
    type: "Point";
    coordinates: [number, number]; // [lng, lat] — GeoJSON convention
  };
  properties: {
    index: number;
    label: string;
    elevation?: number;
    terrain?: string;
  };
}

export type RouteStatus = "idle" | "loading" | "success" | "error";
