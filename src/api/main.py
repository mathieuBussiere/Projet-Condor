from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware

from src.api.v1.router import api_router

app = FastAPI()
app.state.grid_cache = {}
origins = [
    "http://localhost:3000",
    "http://localhost:5173",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:5173",
]

# 2. Add the middleware to the app
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,           # Allow your React app
    allow_credentials=True,
    allow_methods=["*"],              # Allows POST, OPTIONS, GET, etc.
    allow_headers=["*"],              # Allows Content-Type, Authorization, etc.
)
app.include_router(api_router, prefix="/api/v1")