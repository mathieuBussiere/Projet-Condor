"""
Export endpoints for trajectories (GPX, etc.)
"""
from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
import traceback

from src.api.schemas.export import RouteExportRequest
from src.api.services.export import ExportService

router = APIRouter()


@router.post("/gpx")
async def export_route_gpx(request: RouteExportRequest) -> Response:
    """
    Export a route as a GPX file.

    Takes start, end, and custom waypoints.
    Returns a downloadable .gpx file.
    """
    try:
        # Convert to GPX
        gpx_content = ExportService.export_to_gpx(request)

        # Return as downloadable file
        return Response(
            content=gpx_content,
            media_type="application/gpx+xml",
            headers={
                "Content-Disposition": f"attachment; filename={request.trajectory_id}.gpx"
            },
        )
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"GPX export failed: {str(e)}",
        )

@router.post("/geojson")
async def export_route_geojson(request: RouteExportRequest) -> Response:
    """
    Export a route as a GeoJSON file.
    Takes start, end, and custom waypoints.
    Returns a downloadable .geojson file.
    """
    try:
        geojson_content = ExportService.export_to_geojson(request)
        return Response(
            content=geojson_content,
            media_type="application/geo+json",
            headers={
                "Content-Disposition": f"attachment; filename={request.trajectory_id}.geojson"
            },
        )
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"GeoJSON export failed: {str(e)}",
        )


@router.post("/kml")
async def export_route_kml(request: RouteExportRequest) -> Response:
    """
    Export a route as a KML file.
    Takes start, end, and custom waypoints.
    Returns a downloadable .kml file.
    """
    try:
        kml_content = ExportService.export_to_kml(request)
        return Response(
            content=kml_content,
            media_type="application/x-kml+xml",
            headers={
                "Content-Disposition": f"attachment; filename={request.trajectory_id}.kml"
            }
        )
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"KML export failed: {str(e)}",
        )