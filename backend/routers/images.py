import sys
from pathlib import Path
from fastapi import APIRouter
from fastapi.responses import FileResponse
from pydantic import BaseModel

# Allow importing the agent from the repo root agents/ folder
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "agents"))
from building_image_agent import generate_building_image

router = APIRouter(prefix="/building", tags=["images"])


class ImageRequest(BaseModel):
    prompt: str


@router.post("s/generate-image")
def generate_image(req: ImageRequest):
    """
    Generate a 2D front-elevation building image from a natural language description.
    Returns the image file directly, or an error JSON if NeMoTron is offline.
    """
    try:
        result = generate_building_image(req.prompt)
    except Exception as e:
        return {"error": f"Image agent unavailable: {type(e).__name__}"}

    if "error" in result:
        return {"error": result["error"]}

    return FileResponse(
        result["image_path"],
        media_type="image/png",
        headers={"X-Building-Params": str(result["params"])},
    )
