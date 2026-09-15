import json
import uuid

from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from pydantic import ValidationError

from src.api.services.compare_path import RouteComparisonService
from cost_model.weights import HIKING_WEIGHTS
from data.Elevation.structures_elevation import DEMType
from data.data_fetcher import fetch_terrain
from data.structures_communes import BBox
from src.api.schemas.path import PathRequest, PathResponse,RouteComparisonMetadata
from src.api.services.path import PathService

router = APIRouter()


@router.get("/")
async def get_path_status():
    """
    Health check for the spatial path module.
    """
    return {"module": "spatial_path", "status": "online"}


@router.post("/calculate", response_model=PathResponse)
async def calculate_trajectory(request: PathRequest):
    """
    Receives raw lat/lng for start and end points
    to calculate a path or trajectory for Condor.
    """
    try:
        result = PathService.calculate_path(request)
        return result
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Internal spatial engine error: {str(e)}"
        )


@router.post("/compare-route")
async def compare_route(
        file: UploadFile = File(..., description="The uploaded GPX or CSV track"),
        bbox: str = Form(..., description="Stringified JSON of the bounding box"),
        calculated_points: str = Form(..., description="Stringified JSON list of coordinates")
):
    try:
        try:
            raw_metadata = {
                "bbox": json.loads(bbox),
                "calculated_points": json.loads(calculated_points)
            }
        except (json.JSONDecodeError, TypeError):
            raise HTTPException(
                status_code=400,
                detail="Metadata fields (bbox or calculated_points) are not valid JSON strings."
            )

        try:
            metadata = RouteComparisonMetadata.model_validate(raw_metadata)
        except ValidationError as val_error:
            raise HTTPException(
                status_code=422,
                detail=val_error.errors()
            )

        algo_points = [(p.lat, p.lng) for p in metadata.calculated_points]
        file_name = file.filename

        if not algo_points:
            raise HTTPException(status_code=400, detail="calculated_points array cannot be empty.")

        file_bytes = await file.read()
        file_content = file_bytes.decode("utf-8-sig", errors="ignore")

        coordonnees_reference = RouteComparisonService.parse_trail_file(file_name, file_content)
        if not coordonnees_reference:
            raise HTTPException(
                status_code=400,
                detail=f"Could not extract valid coordinate sequences from uploaded file: '{file_name}'"
            )

        domain_bbox = BBox(
            sud=metadata.bbox.sud,
            ouest=metadata.bbox.ouest,
            nord=metadata.bbox.nord,
            est=metadata.bbox.est,
        )

        fetch_terrain(domain_bbox, DEMType.COP30, HIKING_WEIGHTS)
        print(f"[+] DEM data fetched for bounding box: {domain_bbox.dem_data}")
        if not hasattr(domain_bbox, 'dem_data') or domain_bbox.dem_data is None:
            raise HTTPException(
                status_code=500,
                detail="Failed to successfully load terrain matrix mapping details for target bounding box."
            )


        analysis = RouteComparisonService.compare(
            path_algo=algo_points,
            path_ref_raw=coordonnees_reference,
            dem_array=domain_bbox.dem_data.array,
            transform=domain_bbox.dem_data.transform,
            start_tuple=algo_points[0],
            end_tuple=algo_points[-1]
        )

        return {
            "trajectory_id": f"CMP-{uuid.uuid4().hex[:6].upper()}",
            "comparison": analysis
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Comparison Engine failure: {str(e)}")