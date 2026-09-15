from typing import List

from pydantic import BaseModel

from src.api.schemas import Coordinate


class RouteExportRequest(BaseModel):
    trajectory_id: str
    name_track: str
    start: Coordinate
    end: Coordinate
    points: List[Coordinate] = []