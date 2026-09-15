import type { PathRequest, PathResponse } from "../types/Path";

const BASE_URL = "/api/v1/path";

/**
 * Sends coordinates to the FastAPI backend to calculate a trajectory.
 */
export const calculateTrajectory = async (
  request: PathRequest,
): Promise<PathResponse> => {
  try {
    const response = await fetch(`${BASE_URL}/calculate`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(request),
    });

    if (!response.ok) {
      // Handles 422 Unprocessable Entity or 500 Internal Server errors
      const errorDetail = await response.json();
      throw new Error(errorDetail.detail || "Failed to calculate trajectory");
    }

    return await response.json();
  } catch (error) {
    console.error("Condor API Error:", error);
    throw error;
  }
};
