from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
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
    session_id: str = Field(
        "default",
        max_length=100,
        description="Chat session id. Memory is kept per session and resets on server restart.",
    )


class AdvisoryResponse(BaseModel):
    question: str
    location: str | None = None
    activity: str | None = None
    when: str | None = None
    weather: dict | None = None
    sop: dict | None = None
    also_applicable: list[dict] = []
    error: str | None = None
    response: str


PAGE = r"""<!doctype html>
<html>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Weather Advisory Bot</title>
<style>
  body{font-family:Arial,sans-serif;max-width:640px;margin:20px auto;padding:0 12px}
  #chat{border:1px solid #ccc;border-radius:8px;height:60vh;overflow-y:auto;padding:10px;margin-bottom:10px}
  .m{margin:8px 0;padding:8px 10px;border-radius:8px;white-space:pre-wrap}
  .u{background:#dbeafe;margin-left:15%}
  .b{background:#f1f5f9;margin-right:15%}
  .meta{font-size:12px;color:#555;margin-top:4px}
  form{display:flex;gap:6px}
  input{flex:1;padding:10px}
  button{padding:10px 16px}
</style>
</head>
<body>
<h2>Weather Advisory Bot</h2>
<div id="chat"></div>
<form id="f">
  <input id="q" placeholder="e.g. Is it safe to cycle in Bhopal today?" autocomplete="off" required>
  <button id="b">Send</button>
</form>
<script>
const sid = (window.crypto && crypto.randomUUID) ? crypto.randomUUID() : String(Date.now());
const chat = document.getElementById("chat"), q = document.getElementById("q"), b = document.getElementById("b");

function add(cls, text, meta) {
  const d = document.createElement("div");
  d.className = "m " + cls;
  d.textContent = text;
  if (meta) {
    const s = document.createElement("div");
    s.className = "meta";
    s.textContent = meta;
    d.appendChild(s);
  }
  chat.appendChild(d);
  chat.scrollTop = chat.scrollHeight;
  return d;
}

document.getElementById("f").onsubmit = async (e) => {
  e.preventDefault();
  const text = q.value.trim();
  if (!text) return;
  q.value = "";
  add("u", text);
  b.disabled = true;
  const wait = add("b", "Checking...");
  try {
    const r = await fetch("/advice", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({question: text, session_id: sid})
    });
    const d = await r.json();
    if (!r.ok) throw new Error(d.detail || "Request failed");
    wait.remove();
    add("b", d.response, d.sop ? ("Policy: " + d.sop.id + " | severity: " + d.sop.severity + " | activity: " + d.activity) : ("Policy: none applies | activity: " + d.activity));
  } catch (err) {
    wait.remove();
    add("b", "Error: " + err.message);
  } finally {
    b.disabled = false;
    q.focus();
  }
};
</script>
</body>
</html>
"""


@app.get("/", response_class=HTMLResponse)
async def home():
    return PAGE


@app.get("/health")
def health():
    """Health-check endpoint."""
    return {"status": "healthy"}


@app.post("/advice", response_model=AdvisoryResponse)
def get_advice(request: AdvisoryRequest):
    """Generate a weather advisory for the user's question."""
    try:
        return run_advisor(request.question, request.session_id)
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Unable to process the advisory request: {exc}",
        ) from exc