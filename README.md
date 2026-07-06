## Revocab
A website that gives you alternative vocabulary by typing a typical and boring word you keep using or by defining it if you don't know any other else to say it.

LLM APIs via Google Gemini
Next.js, React, and Typescript
Python w/ FastAPI

## Local development

Run the two servers in separate terminals:

```
uvicorn lib.main:app --reload   # backend on :8000
npm run dev                     # frontend on :3000
```