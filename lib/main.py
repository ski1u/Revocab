from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from pydantic import BaseModel
from google import genai
from google.genai import types

import requests
from dotenv import load_dotenv
import os
import json

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

def get_dictionary(word: str) -> dict:
    # Fetches a signal to Free Dictionary API with a word parameter,
    # then returns a dictionary full of informative data
    res = requests.get(f"https://api.dictionaryapi.dev/api/v2/entries/en/{word}")
    if (x := res.status_code) != 200: return { "error": f"Failed to fetch data. Status code: {x}" }
    return res.json()

# ---

class ChatRequest(BaseModel):
    message: str
schema = '{"word": "example", "pronunciation": "əɡˈzæmpl̩", "definition": "a representative instance"}'
word_history: list[types.Content] = []

# ---

def stream_chat(message: str):
    yield f"data: {json.dumps({"status": "thinking"})}\n\n"

    word_history.clear()

    res = client.models.generate_content_stream(
        contents=message,
        model="gemini-2.5-flash",
        config=types.GenerateContentConfig(
            tools=[get_dictionary],
            system_instruction=f"""
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
                """,
            max_output_tokens=max_tokens,
            temperature=0.6,
            thinking_config=types.ThinkingConfig(thinking_budget=320)
        )
    ); res_text = ""

    for chunk in res:
        if (x := chunk.text):
            res_text += x
            yield f"data: {json.dumps({"chunk": x})}\n\n"
    yield f"data: {json.dumps({"done": True, "reply": res_text})}\n\n"

def stream_rotate():
    None

# ---

@app.post("/chat")
def chat(req: ChatRequest):
    return StreamingResponse(
        stream_chat(req.message),
        media_type="text/event-stream"
    )

class RotateRequest(BaseModel):
    input_from: str
    word: str

@app.post("/rotate")
def rotate(req: RotateRequest):
    word_history.append(
        types.Content(role="model", parts=[types.Part(text=req.word)])
    )

    res = client.models.generate_content_stream(
        contents=f"Original input word/definition: {req.input_from}\nExclude: {word_history}",
        model="gemini-2.5-flash",
        config=types.GenerateContentConfig(
            tools=[get_dictionary],
            system_instruction=f"""
                You will be given either an original word or a definition of a word
                and will assist in choosing back with a different best-fit,
                high-utility, high-frequency, and professional vocabulary word
                in daily human life. The vocabulary word must not be the same
                original word as what the user provided and what's in word_history.
                The vocabulary word must NOT be low-frequency, highly specific, or obscure jargon.

                Using your chosen word, use the get_dictionary tool that takes a parameter, word, string,
                which is a word with no spaces, lowercased, to fetch information
                about a word. You'll be returned a dictionary. Based off of that,
                you will respond back with JSON in this format, no markdown:
                {schema}, by choosing the necessary data you got from the
                get_dictionary tool result.
                """,
            max_output_tokens=max_tokens,
            temperature=0.6,
            thinking_config=types.ThinkingConfig(thinking_budget=320)
        )
    ); res_text = ""

    for chunk in res:
        if (x := chunk.text):
            res_text += res_text
            yield f"data: {json.dumps({"chunk": x})}\n\n"
    yield f"data: {json.dump({"done": True, "reply": res_text})}\n\n"