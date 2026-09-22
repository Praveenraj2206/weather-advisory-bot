from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from graph import run_advisor


app = FastAPI(
    title="Weather Advisory Support Bot",
    description=(
        "A weather advisory assistant that checks weather conditions "
        "against Standard Operating Procedures (SOPs)."
    ),
    version="1.0.0",
)


class AdvisoryRequest(BaseModel):
    question: str = Field(
        ...,
        min_length=3,
        max_length=1000,
        description="A weather-related question that includes an activity and location.",
        examples=["Is it safe to go cycling in Bengaluru today?"],
    )


class AdvisoryResponse(BaseModel):
    question: str
    location: str | None = None
    activity: str | None = None
    weather: dict | None = None
    sop: dict | None = None
    error: str | None = None
    response: str


@app.get("/")
def home():
    """Basic endpoint to confirm that the API is running."""
    return {
        "message": "Weather Advisory Support Bot is running.",
        "docs": "/docs",
    }


@app.get("/health")
def health():
    """Health-check endpoint."""
    return {"status": "healthy"}


@app.post("/advice", response_model=AdvisoryResponse)
def get_advice(request: AdvisoryRequest):
    """Generate a weather advisory for the user's question."""
    try:
        result = run_advisor(request.question)
        return result

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Unable to process the advisory request: {exc}",
        ) from exc