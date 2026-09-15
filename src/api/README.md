# Condor API

This folder contains the FastAPI-based HTTP API for Condor's spatial path module. The API exposes a versioned router at `/api/v1` and a dedicated path service that computes geodesic metadata (distance, midpoint, estimated time).

## Table of Contents
- [Quick Links](#quick-links)
- [Project Structure](#project-structure)
- [Install Dependencies](#install-dependencies)
- [Run the API](#run-the-api)
- [Endpoints](#endpoints)
- [Step-by-Step Example: Adding a New Feature to the API](#step-by-step-example-adding-a-new-feature-to-the-api)



## Quick Links
- **App Entrypoint:** `src/api/main.py`
- **v1 Router:** `src/api/v1/router.py`
- **Path Endpoints:** `src/api/v1/endpoints/path.py`
- **Request/Response Schemas:** `src/api/schemas/path.py`
- **Business Logic / Service:** `src/api/services/path.py`

---

## Project structure 
The project follows a clean architectural pattern separating validation schemas, network endpoint controllers, and core domain business logic:

```text
api/
├── __init__.py
├── main.py              # Create FastAPI() app, configure CORS and include v1 router
├── schemas/             # Pydantic validation models
│   ├── __init__.py
│   └── path.py          # Definition for Coordinate, PathRequest, and PathResponse
├── services/            # Core business logic / service layers
│   └── path.py          # PathService implementation utilizing geopy.geodesic
└── v1/                  # API Version 1 Namespace
    ├── .gitkeep
    ├── __init__.py
    ├── router.py        # Top-level v1 APIRouter registering health and sub-routers
    └── endpoints/       # Network-facing HTTP request controllers
        └── path.py      # Module status and trajectory calculation endpoints
```
### 1. schemas/ (Data Type)
- What it does: Defines the exact structure (data shape) of incoming requests and outgoing responses using Pydantic models.
- What belongs here: Data models, validation constraints (e.g., ensuring latitudes are between -90 and 90), and type hints.

### 2. services/ (Business Logic)
- What it does: Contains the core computational logic that implements the actual path calculations, distance computations
- What belongs here: Pure Python functions and classes that perform the necessary calculations without any knowledge of HTTP or FastAPI.

### 3. v1/ (API Version Namespace)
- What it does: Organizes all API endpoints under a versioned namespace (`/api/v1`) to allow for future expansion and backward compatibility.
- What belongs here: FastAPI routers and endpoint definitions that handle HTTP requests, invoke the appropriate service functions, and return responses.

## Install dependencies
Dependencies are listed in `SetUp/requirements.txt`. From the project root run:
```bash
python -m pip install -r SetUp/requirements.txt

## Run the API
From the project root, start the API with:
```bash
# recommended: ensure the project root is on PYTHONPATH
PYTHONPATH=. uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000
```
Or from the `src/api` directory:
```bash
uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000
```
## Interactive API docs will be available at:
* Swagger UI: http://127.0.0.1:8000/docs
* ReDoc: http://127.0.0.1:8000/redoc

## Endpoints

### 1. Global Health Monitor
* **URL Target:** `GET /api/v1/health`
* **Purpose:** Basic API-level health validation checks (registered in `src/api/v1/router.py`).
* **Current Implementation Output:**
  ```json
  {"ping"}
    ```
### 2. Path Calculation
* **URL Target:** `GET /api/v1/path/`
* **Purpose:** Compute geodesic metadata (distance, midpoint, estimated time) between two coordinates.
* **Request Body Schema:**
```json
{
  "module": "spatial_path",
  "status": "online"
}
```

### 3. Path Calculator
* **URL Target:** `POST /api/v1/path/calculate`
* **Purpose:** Calculate a path/trajectory between two coordinates.
* **Request Body Schema (PathRequest):**
```json
{
  "start": {
    "lat": 45.4010,
    "lng": -71.8922
  },
  "end": {
    "lat": 45.6020,
    "lng": -71.5015
  }
}
```
* **Response Body Schema (PathResponse):**
```json
{
  "trajectory_id": "TRJ-A2B4E9",
  "points": [
    {
      "lat": 45.5015,
      "lng": -71.69685
    }
  ],
  "distance_km": 37.42,
  "time": 449.0
}
```

## Step-by-Step Example: Adding a New Feature to the API
Let's say your system needs a new feature: A weather alert system for a bounding box perimeter. Here is exactly how you would build it across your codebase:
1. **Define the Request/Response Schemas** (in `src/api/schemas/weather.py`):
```python
from pydantic import BaseModel

# What the client must send
class WeatherAlertRequest(BaseModel):
    north: float
    south: float
    east: float
    west: float

# What the API will return back
class WeatherAlertResponse(BaseModel):
    has_alert: bool
    condition: str
    severity: str
```
Step 2: Write the Calculation Logic (`api/services/weather.py`)
Create a service class that handles the domain operations entirely separated from FastAPI.
```python
from ..schemas.weather import WeatherAlertRequest, WeatherAlertResponse

class WeatherService:
    @staticmethod
    def check_bbox_alerts(bounds: WeatherAlertRequest) -> WeatherAlertResponse:
        """
        Pure business logic. Imagine this fetches raw radar data 
        for the given north/south/east/west coordinates.
        """
        # (Mock logic for example illustration)
        if bounds.north > 45.5:
            return WeatherAlertResponse(has_alert=True, condition="Thunderstorm", severity="High")
        
        return WeatherAlertResponse(has_alert=False, condition="Clear", severity="None")
```
Step 3: Create the Endpoint (`api/v1/endpoints/weather.py`)
Create the endpoint handler to wire up the HTTP routing channel.
```python
from fastapi import APIRouter, HTTPException
from ...schemas.weather import WeatherAlertRequest, WeatherAlertResponse
from ...services.weather import WeatherService

router = APIRouter()

@router.post("/check-bounds", response_model=WeatherAlertResponse)
def check_bounding_box_weather(payload: WeatherAlertRequest):
    """
    HTTP interface endpoint. Receives payload, validates via schema,
    hands it to the Service, and returns the response object.
    """
    try:
        result = WeatherService.check_bbox_alerts(payload)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Weather core error: {str(e)}")

```
Step 4: Register with your Root Router (`api/v1/router.py`)
Finally, mount your new sub-router file into your primary system mapping ecosystem so it becomes accessible under the global application instance prefix.
```python
from fastapi import APIRouter
from src.api.v1.endpoints.path import router as path_router
from src.api.v1.endpoints.weather import router as weather_router # 1. Import it

api_router = APIRouter()

# Register routes
api_router.include_router(path_router, prefix="/path", tags=["Spatial Path Operations"])
api_router.include_router(weather_router, prefix="/weather", tags=["Atmospheric Alerts"]) # 2. Mount it

@api_router.get("/health")
def health_check():
    return {"status": "ok"}
```
### The Result
Your new feature is fully integrated! The client application can now make a structured HTTP request to:
POST http://127.0.0.1:8000/api/v1/weather/check-bounds