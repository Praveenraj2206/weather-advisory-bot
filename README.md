# Weather Advisory Support Bot

A weather advisory assistant that checks weather conditions against predefined Standard Operating Procedures (SOPs) and provides activity-specific guidance.

The application uses **FastAPI** to expose an API, **LangGraph** to coordinate the workflow, **Groq** to interpret questions and generate responses, and **Open-Meteo** to retrieve weather information.

## Features

* Understands natural-language weather questions.
* Extracts the requested activity and location.
* Converts a location into coordinates using Open-Meteo geocoding.
* Retrieves current weather information.
* Matches weather measurements against configurable SOP rules.
* Supports simple comparisons and combined `all`/`any` conditions.
* Returns an advisory when a rule matches.
* Provides a fallback response when no applicable SOP is found.
* Exposes API endpoints through FastAPI.
* Includes automated tests for policy matching and API behavior.

## Technology Stack

| Component                  | Technology                      |
| -------------------------- | ------------------------------- |
| API framework              | FastAPI                         |
| Workflow orchestration     | LangGraph                       |
| Language-model integration | LangChain with Groq             |
| Language model             | Configured through `GROQ_MODEL` |
| Weather data               | Open-Meteo                      |
| Data format for SOPs       | JSON                            |
| Validation                 | Pydantic                        |
| Testing                    | Python `unittest`               |

## Project Structure

```text
weather-advisory-bot/
│
├── app.py
├── graph.py
├── weather.py
├── policies.py
├── sops.json
├── requirements.txt
├── .env.example
├── .gitignore
├── README.md
│
└── evals/
    └── test_cases.py
```

### File Responsibilities

* **`app.py`** — Defines the FastAPI application and its endpoints.
* **`graph.py`** — Builds the LangGraph workflow and coordinates question understanding, location resolution, weather retrieval, SOP matching, and response generation.
* **`weather.py`** — Communicates with Open-Meteo to geocode locations and retrieve weather information.
* **`policies.py`** — Loads SOPs and evaluates their conditions against weather data.
* **`sops.json`** — Stores the advisory rules, conditions, severity, and advice.
* **`evals/test_cases.py`** — Contains automated tests for policy logic and API behavior.
* **`.env.example`** — Provides an example of the environment variables required to run the application.

## Workflow

```text
User submits a weather question
             |
             v
Understand question using Groq
             |
             v
Extract activity and location
             |
             v
Resolve location using Open-Meteo
             |
             v
Fetch weather data
             |
             v
Evaluate applicable SOP conditions
             |
             v
Generate advisory using Groq
             |
             v
Return response through FastAPI
```

If the location cannot be resolved or weather data cannot be retrieved, the workflow returns an error response. If no applicable SOP matches, the bot returns a no-specific-guidance response.

## Prerequisites

* Python 3.12 or a compatible Python version.
* A Groq API key.
* Internet access for Groq and Open-Meteo requests.

## Installation and Setup

### 1. Clone or open the project

Open the project directory in VS Code and open a terminal in that directory.

### 2. Create a virtual environment

```bash
python -m venv venv
```

Activate it in Git Bash on Windows:

```bash
source venv/Scripts/activate
```

### 3. Install dependencies

```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Configure environment variables

Copy the example environment file:

```bash
cp .env.example .env
```

Add your Groq API key and model configuration to `.env`:

```env
GROQ_API_KEY=your_groq_api_key_here
GROQ_MODEL=llama-3.3-70b-versatile
```

Replace the placeholder with your own API key. Keep `.env` private and do not commit it to Git.

### 5. Start the server

```bash
uvicorn app:app --reload
```

The development server will be available at:

```text
http://127.0.0.1:8000
```

Interactive API documentation:

```text
http://127.0.0.1:8000/docs
```

Health check:

```text
http://127.0.0.1:8000/health
```

## API Usage

### Health Check

**Request**

```http
GET /health
```

**Example response**

```json
{
  "status": "healthy"
}
```

### Request an Advisory

**Request**

```http
POST /advice
Content-Type: application/json
```

**Example request body**

```json
{
  "question": "Would today be a good day for a picnic in Bengaluru?"
}
```

**Example response structure**

```json
{
  "question": "Would today be a good day for a picnic in Bengaluru?",
  "location": "Bengaluru, Karnataka, India",
  "activity": "picnic",
  "weather": {
    "temperature": 26.1,
    "wind_speed": 12.7,
    "precipitation_probability": 2
  },
  "sop": {
    "id": "SOP-05",
    "severity": "low"
  },
  "error": null,
  "response": "The weather looks suitable for a picnic..."
}
```

The values above illustrate the response structure. Actual weather values and the matching SOP depend on the weather service response and the rules in `sops.json`.

## SOP Policy Matching

The policy engine reads the rules from `sops.json`.

Supported operators:

| Operator  | Meaning                                   |
| --------- | ----------------------------------------- |
| `>`       | Greater than                              |
| `<`       | Less than                                 |
| `>=`      | Greater than or equal to                  |
| `<=`      | Less than or equal to                     |
| `==`      | Equal to                                  |
| `between` | Within an inclusive lower and upper bound |

Combined conditions can use:

* **`all`** — Every listed condition must match.
* **`any`** — At least one listed condition must match.

The policy engine checks activity-specific SOPs and can also consider general outdoor rules. The first matching rule is returned.

### Included SOP Categories

The initial rules cover:

* Cycling
* Walking
* Picnics
* Children outdoors
* Travel
* Elderly people outdoors
* Hiking
* General outdoor conditions

These rules are configurable in `sops.json`.

## Running Automated Tests

Run the test suite from the project root:

```bash
python -m unittest discover -s evals -p "test_cases.py" -v
```

The tests cover policy matching, combined conditions, missing weather fields, threshold boundaries, the health endpoint, and the advice endpoint.

The API response test uses a mocked workflow result. This keeps that test independent of live weather services and Groq calls.

## Design Decisions

### Open-Meteo

Open-Meteo provides geocoding and weather endpoints for this project. The weather integration does not require a key in the basic implementation.

### Groq

Groq is used through LangChain to interpret user questions and generate readable explanations. The model name is configurable through the `GROQ_MODEL` environment variable.

### JSON-Based SOPs

Keeping the SOPs in JSON separates advisory policy data from the Python implementation. Rules can be edited without changing the policy evaluation functions, provided the JSON structure and supported operators are followed.

### LangGraph

LangGraph organizes the application into distinct workflow steps, making the processing sequence easier to understand, maintain, and extend.

## Limitations and Future Improvements

* The advisory quality depends on the accuracy and availability of the weather service.
* The current SOP collection is a sample rule set and is not a substitute for official weather warnings or professional safety guidance.
* The current policy engine returns the first matching SOP rather than combining all matching rules or prioritizing severity.
* Activity extraction depends on the configured language model.
* The automated tests do not yet comprehensively test live external-service failures, every SOP, or every workflow branch.
* Additional tests could mock geocoding, weather retrieval, and model responses to verify error handling deterministically.
* Future improvements could include a user interface, richer location handling, additional SOP categories, more extensive evaluation cases, and deployment configuration.

## Security Notes

* Store API credentials in `.env`.
* Do not commit `.env` or expose API keys in source code, screenshots, or logs.
* Use environment variables for deployment secrets.
* Consider adding request limits, structured logging, and more detailed error handling before production deployment.

## License

Add the license required by your project or assignment before distributing the application.
