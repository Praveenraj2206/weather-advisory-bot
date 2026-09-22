from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from fastapi.responses import HTMLResponse
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


@app.get("/", response_class=HTMLResponse)
async def home():
    return """
    <html>
    <head>
        <title>Weather Advisory Bot</title>
    </head>

    <body style="font-family: Arial; background-color: #eef4ff;">

        <div style="width: 500px; margin: 50px auto; padding: 25px;
                    background-color: white; border-radius: 10px;
                    box-shadow: 0 0 10px lightgray;">

            <h1 style="text-align: center; color: #2563eb;">
                Weather Advisory Bot
            </h1>

            <p style="text-align: center;">
                Ask a question about the weather and get useful advice.
            </p>

            <form id="myForm">
                <label>Enter your question:</label>
                <br><br>

                <textarea id="question" rows="4"
                    style="width: 100%; box-sizing: border-box; padding: 10px;"
                    placeholder="Example: Would today be a good day for a picnic in Bengaluru?"
                    required></textarea>

                <br><br>

                <button type="submit"
                    style="width: 100%; padding: 12px; background-color: #2563eb;
                           color: white; border: none; border-radius: 5px;">
                    Get Weather Advice
                </button>
            </form>

            <div id="result"
                style="display: none; margin-top: 25px; padding: 15px;
                       background-color: #f1f5f9; border-radius: 8px;">

                <h3 style="color: #2563eb;">Your Weather Advice</h3>
                <p id="answer"></p>
                <p id="sop"></p>
                <p id="severity"></p>
                <p id="weather"></p>

            </div>
        </div>

        <script>
            document.getElementById("myForm").onsubmit = async function(event) {
                event.preventDefault();

                let question = document.getElementById("question").value.trim();
                let result = document.getElementById("result");
                let button = document.querySelector("button");

                result.style.display = "block";
                document.getElementById("answer").innerText = "Checking weather...";
                document.getElementById("sop").innerText = "";
                document.getElementById("severity").innerText = "";
                document.getElementById("weather").innerText = "";

                button.disabled = true;

                try {
                    let response = await fetch("/advice", {
                        method: "POST",
                        headers: {
                            "Content-Type": "application/json"
                        },
                        body: JSON.stringify({question: question})
                    });

                    let data = await response.json();

                    if (!response.ok) {
                        throw new Error(data.detail || "Unable to get advice.");
                    }

                    let sop = data.sop || {};
                    let weather = data.weather || {};

                    document.getElementById("answer").innerText =
                        "Answer: " + (data.response || "No advice available.");

                    document.getElementById("sop").innerText =
                        "SOP ID: " + (sop.id || "No matching SOP");

                    document.getElementById("severity").innerText =
                        "Severity: " + (sop.severity || "Not specified");

                    document.getElementById("weather").innerText =
                        "Weather: Temperature: " + (weather.temperature ?? "N/A") + "°C, " +
                        "Precipitation: " + (weather.precipitation_probability ?? "N/A") + "%, " +
                        "Wind speed: " + (weather.wind_speed ?? "N/A") + " km/h";

                } catch (error) {
                    document.getElementById("answer").innerText =
                        "Error: " + error.message;
                } finally {
                    button.disabled = false;
                }
            };
        </script>

    </body>
    </html>
    """

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