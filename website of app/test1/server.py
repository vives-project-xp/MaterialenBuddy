import asyncio
import contextlib
import json
import os
import sys
import uuid
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel


BASE_DIR = Path(__file__).parent
WAYPOINTS_FILE = BASE_DIR / "waypoints.json"
CREATE3_MODE = os.getenv("CREATE3_MODE", "mock").lower()
CREATE3_IP = os.getenv("CREATE3_IP", "10.10.234.52")
NAVIGATION_TIMEOUT_SECONDS = 60


class NavigateRequest(BaseModel):
    location_id: str


class NavigationStatus(BaseModel):
    job_id: str
    status: str
    location_id: str
    message: str


app = FastAPI(title="MaterialenBuddy Create 3 API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
jobs: dict[str, NavigationStatus] = {}
active_task: asyncio.Task[None] | None = None


def load_waypoints() -> list[dict[str, Any]]:
    with WAYPOINTS_FILE.open(encoding="utf-8") as file:
        return json.load(file)


def find_waypoint(location_id: str) -> dict[str, Any]:
    waypoint = next(
        (item for item in load_waypoints() if item["id"] == location_id),
        None,
    )
    if waypoint is None:
        raise HTTPException(status_code=404, detail="Onbekende locatie")
    return waypoint


@app.get("/", include_in_schema=False)
async def index() -> FileResponse:
    return FileResponse(BASE_DIR / "index.html")


@app.get("/locations")
async def locations() -> list[dict[str, Any]]:
    return load_waypoints()


@app.get("/robot")
async def robot_info() -> dict[str, str]:
    return {
        "ip": CREATE3_IP,
        "mode": CREATE3_MODE,
        "sdk": "irobot-edu-sdk",
        "message": "Bluetooth-navigatie actief." if CREATE3_MODE == "bluetooth" else "Mocknavigatie actief.",
    }


async def run_navigation(job_id: str, waypoint: dict[str, Any]) -> None:
    process: asyncio.subprocess.Process | None = None
    jobs[job_id] = NavigationStatus(
        job_id=job_id,
        status="onderweg",
        location_id=waypoint["id"],
        message=f"Onderweg naar {waypoint['naam']}...",
    )
    try:
        if CREATE3_MODE == "mock":
            await asyncio.sleep(2)
        elif CREATE3_MODE == "bluetooth":
            process = await asyncio.create_subprocess_exec(
                sys.executable,
                str(BASE_DIR / "bluetooth_navigate.py"),
                str(waypoint["x"]),
                str(waypoint["y"]),
                str(waypoint["yaw"]),
            )
            try:
                return_code = await asyncio.wait_for(
                    process.wait(), timeout=NAVIGATION_TIMEOUT_SECONDS
                )
            except asyncio.TimeoutError as error:
                process.kill()
                await process.wait()
                raise RuntimeError("Navigatie timeout na 60 seconden.") from error
            if return_code != 0:
                raise RuntimeError(f"Bluetooth-navigatie stopte met code {return_code}.")
        else:
            raise RuntimeError("Onbekende CREATE3_MODE. Gebruik mock of bluetooth.")
        jobs[job_id] = NavigationStatus(
            job_id=job_id,
            status="aangekomen",
            location_id=waypoint["id"],
            message=f"Aangekomen bij {waypoint['naam']}.",
        )
    except asyncio.CancelledError:
        if process is not None and process.returncode is None:
            process.kill()
            await process.wait()
        jobs[job_id] = NavigationStatus(
            job_id=job_id,
            status="geannuleerd",
            location_id=waypoint["id"],
            message="Navigatie geannuleerd.",
        )
        raise
    except Exception as error:
        jobs[job_id] = NavigationStatus(
            job_id=job_id,
            status="fout",
            location_id=waypoint["id"],
            message=str(error),
        )


@app.post("/navigate", response_model=NavigationStatus, status_code=202)
async def navigate(request: NavigateRequest) -> NavigationStatus:
    global active_task
    waypoint = find_waypoint(request.location_id)
    if active_task is not None and not active_task.done():
        active_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await active_task
    job_id = str(uuid.uuid4())
    jobs[job_id] = NavigationStatus(
        job_id=job_id,
        status="gestart",
        location_id=waypoint["id"],
        message=f"Navigatie naar {waypoint['naam']} gestart.",
    )
    task = asyncio.create_task(run_navigation(job_id, waypoint))
    active_task = task
    try:
        await asyncio.wait_for(asyncio.shield(task), timeout=0.1)
    except asyncio.TimeoutError:
        pass
    return jobs[job_id]


@app.get("/status/{job_id}", response_model=NavigationStatus)
async def status(job_id: str) -> NavigationStatus:
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Onbekende navigatiejob")
    return jobs[job_id]