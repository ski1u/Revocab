from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from google import genai
from google.genai import types

from dotenv import load_dotenv
import os

load_dotenv()

app = FastAPI()
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"]
)

class ChatRequest(BaseModel):
    message: str

schema = '{"word": "example", "pronunciation": "ig-zam-puhl", "definition": "a representative instance"}'

@app.post("/chat")
def chat(req: ChatRequest):
    res = client.models.generate_content(
        contents=req.message,
        model="gemini-2.5-flash",
        config=types.GenerateContentConfig(
            system_instruction=f"""
                You will be given either a word or a definition of a word
                and will assist in responding back with a different, best-fit,
                high-utility, high-frequency, and professional vocabulary word
                in daily human life. The vocabulary word must NOT be low-frequency,
                highly specific, obscure jargon. Respond back with JSON in this format, no markdown:
                {schema}. The input field should be the user's exact message input
                """,
            max_output_tokens=1024,
            temperature=0.6,
            response_mime_type="application/json",
            thinking_config=types.ThinkingConfig(thinking_budget=320)
        )
    )
    return { "reply": res.text }

class RotateRequest(BaseModel):
    input: str
    word: str

@app.post("/rotate")
def rotate(req: RotateRequest):
    res = client.models.generate_content(
        contents=f"Input: {req.input}\nExclude: {req.word}",
        model="gemini-2.5-flash",
        config=types.GenerateContentConfig(
            system_instruction=f"""
                You will be given a user's previous input message that
                highlights either a word or a definition of a word,
                and a vocabulary word that was given to the user by you in
                previous messages.
                You will assist in responding back with a DIFFERENT, best-fit,
                high-utility, high-frequency, and professional vocabulary word
                in daily human life. The vocabulary word must NOT be low-frequency,
                highly specific, obscure jargon. You must NOT return the
                excluded word. Respond back with JSON in this format, no markdown:
                {schema}. The input field should be the user's exact message input
                """,
            max_output_tokens=1024,
            temperature=0.6,
            response_mime_type="application/json",
            thinking_config=types.ThinkingConfig(thinking_budget=320)
        )
    )
    return { "reply": res.text }