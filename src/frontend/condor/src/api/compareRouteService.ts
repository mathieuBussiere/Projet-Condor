import type { RouteComparisonResponse } from "../types/CompareRoute";

const BASE_URL = "/api/v1/path";

/**
 * Executes a route comparison by streaming a local trace file
 * and its metadata directly to the backend processing engine.
 */
export async function compareRoute(
  file: File,
  bbox: { sud: number; ouest: number; nord: number; est: number },
  calculatedPoints: { lat: number; lng: number }[],
): Promise<RouteComparisonResponse> {
  try {
    const formData = new FormData();

    formData.append("file", file);

    formData.append("bbox", JSON.stringify(bbox));
    formData.append("calculated_points", JSON.stringify(calculatedPoints));

    const response = await fetch(`${BASE_URL}/compare-route`, {
      method: "POST",
      body: formData,
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(
        errorData.detail || `Server responded with status: ${response.status}`,
      );
    }

    const data: RouteComparisonResponse = await response.json();
    return data;
  } catch (error) {
    console.error("[-] Error executing route comparison:", error);
    throw error;
  }
}
