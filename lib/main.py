from fastapi import FastAPI, Request, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from pydantic import BaseModel
from google import genai
from google.genai import types

import requests
from dotenv import load_dotenv
import os
import json
import time

load_dotenv()

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
max_tokens = 640
app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"]
)

# --- Rate limiting (server-side, per client IP) ---

RATE_LIMIT_SECONDS = 3.0
_last_request: dict[str, float] = {}  # ip -> last accepted request time

def rate_limit(request: Request):
    # Runs before the route handler. Enforces a minimum gap between requests
    # from the same IP so the Gemini API can't be spammed. Unlike the client
    # check, this can't be bypassed from the browser.
    ip = request.client.host if request.client else "anon"
    now = time.monotonic()
    if now - _last_request.get(ip, 0.0) < RATE_LIMIT_SECONDS:
        raise HTTPException(
            status_code=429,
            detail="Slow down — please wait a few seconds between requests."
        )
    _last_request[ip] = now

# --- Helpers ---

def sse(data: dict) -> str:
    # Format a dict as one Server-Sent Events frame.
    return f"data: {json.dumps(data)}\n\n"

def get_dictionary(word: str) -> dict:
    # Fetches a signal to Free Dictionary API with a word parameter,
    # then returns a dictionary full of informative data
    res = requests.get(f"https://api.dictionaryapi.dev/api/v2/entries/en/{word}")
    if (x := res.status_code) != 200: return { "error": f"Failed to fetch data. Status code: {x}" }
    return res.json()

# ---

class ChatRequest(BaseModel):
    message: str

class RotateRequest(BaseModel):
    input_from: str
    word: str
    exclude: list[str] = []  # words already shown, sent by the client per request

schema = '{"word": "example", "pronunciation": "əɡˈzæmpl̩", "definition": "a representative instance"}'

CHAT_INSTRUCTION = f"""
    You will be given either a word or a definition of a word
    and will assist in choosing back with a best-fit,
    high-utility, high-frequency, and professional vocabulary word
    in daily human life. The vocabulary word must not be the same
    word as what the user provided.
    The vocabulary word must NOT be low-frequency, highly specific, or obscure jargon.

    Using your chosen word, use the get_dictionary tool that takes a parameter, word, string,
    which is a word with no spaces, lowercased, to fetch information
    about a word. You'll be returned a dictionary. Based off of that,
    you will respond back with JSON in this format, no markdown:
    {schema}, by choosing the necessary data you got from the
    get_dictionary tool result.
    """

ROTATE_INSTRUCTION = f"""
    You will be given an original word or a definition of a word, plus a list
    of words to exclude, and will assist in choosing back with a different
    best-fit, high-utility, high-frequency, and professional vocabulary word
    in daily human life. The vocabulary word must not be the same as the
    original input or any of the words to exclude that are provided.
    The vocabulary word must NOT be low-frequency, highly specific, or obscure jargon.

    Using your chosen word, use the get_dictionary tool that takes a parameter, word, string,
    which is a word with no spaces, lowercased, to fetch information
    about a word. You'll be returned a dictionary. Based off of that,
    you will respond back with JSON in this format, no markdown:
    {schema}, by choosing the necessary data you got from the
    get_dictionary tool result.
    """

def _config(system_instruction: str) -> types.GenerateContentConfig:
    return types.GenerateContentConfig(
        tools=[get_dictionary],
        system_instruction=system_instruction,
        max_output_tokens=max_tokens,
        temperature=0.6,
        thinking_config=types.ThinkingConfig(thinking_budget=320)
    )

# ---

def stream_chat(message: str):
    try:
        yield sse({"status": "thinking"})

        res = client.models.generate_content_stream(
            contents=message,
            model="gemini-2.5-flash",
            config=_config(CHAT_INSTRUCTION)
        )

        res_text = ""
        for chunk in res:
            if (x := chunk.text):
                res_text += x
                yield sse({"chunk": x})
        yield sse({"done": True, "reply": res_text})
    except Exception:
        yield sse({"error": "Something went wrong generating your word. Please try again."})

def stream_rotate(word: str, input_from: str, exclude: list[str]):
    try:
        yield sse({"status": "thinking"})

        # Build the exclude list locally, per request — no shared server state.
        # dict.fromkeys dedupes while preserving order; drop any empty strings.
        excluded = ", ".join(w for w in dict.fromkeys([word, *exclude]) if w)

        res = client.models.generate_content_stream(
            contents=f"Original input word/definition: {input_from}\nExclude these words: {excluded}",
            model="gemini-2.5-flash",
            config=_config(ROTATE_INSTRUCTION)
        )

        res_text = ""
        for chunk in res:
            if (x := chunk.text):
                res_text += x
                yield sse({"chunk": x})
        yield sse({"done": True, "reply": res_text})
    except Exception:
        yield sse({"error": "Something went wrong rotating your word. Please try again."})

# ---

@app.post("/api/chat", dependencies=[Depends(rate_limit)])
def chat(req: ChatRequest):
    return StreamingResponse(
        stream_chat(req.message),
        media_type="text/event-stream"
    )

@app.post("/api/rotate", dependencies=[Depends(rate_limit)])  # Thesarus tool
def rotate(req: RotateRequest):
    return StreamingResponse(
        stream_rotate(word=req.word, input_from=req.input_from, exclude=req.exclude),
        media_type="text/event-stream"
    )
