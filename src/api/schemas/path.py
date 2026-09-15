from typing import Optional, List

from fastapi import Form, File, UploadFile
from pydantic import BaseModel, Field


class Coordinate(BaseModel):
    lat: float = Field(default=45.393, ge=-90.0, le=90.0, description="Latitude in Decimal Degrees")
    lng: float = Field(default=-71.8465, ge=-180.0, le=180.0, description="Longitude in Decimal Degrees")


class BBoxSchema(BaseModel):
    sud: float = Field(..., description="Southern boundary latitude")
    ouest: float = Field(..., description="Western boundary longitude")
    nord: float = Field(..., description="Northern boundary latitude")
    est: float = Field(..., description="Eastern boundary longitude")


class PathRequest(BaseModel):
    start: Coordinate = Field(default_factory=Coordinate)
    end: Coordinate = Field(default_factory=Coordinate)
    bbox: BBoxSchema
    trail_file_name: Optional[str] = None


class PathResponse(BaseModel):
    trajectory_id: str
    start: Coordinate
    end: Coordinate
    bbox: BBoxSchema
    distance_km: float
    time: float  #
    points: list[Coordinate]
    grid_shape: tuple[int, int] | None = None
    grid_computed: bool = False
    max_elevation_m: float | None = None
    avg_elevation_m: float | None = None

class ComparisonMetrics(BaseModel):
    frechet_distance_meters: float
    dtw_corridor_deviation_meters: float
    tobler_effort_ratio: float

class ComparisonAnalysis(BaseModel):
    score: float
    verdict: str
    metrics: ComparisonMetrics

class RouteComparisonRequest(BaseModel):
    file: UploadFile = File(..., description="The uploaded GPX or CSV track"),
    bbox: str = Form(..., description="Stringified BBoxSchema JSON"),
    calculated_points: str = Form(..., description="Stringified list[Coordinate] JSON")

class RouteComparisonMetadata(BaseModel):
    bbox: BBoxSchema
    calculated_points: List[Coordinate]

class RouteComparisonResponse(BaseModel):
    trajectory_id: str
    distance_km: float
    estimated_time_minutes: float
    points: list[Coordinate]
    comparison: ComparisonAnalysis