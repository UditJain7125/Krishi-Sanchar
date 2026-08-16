import os
from dotenv import load_dotenv

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate


load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    raise ValueError("GEMINI_API_KEY is missing from .env")


llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash-lite",
    temperature=0.4,
    google_api_key=api_key
)


prompt = ChatPromptTemplate.from_messages([
    ("system", """ You are an AI Farming Assistant.

        Help farmers with:
        - Crop cultivation
        - Soil management
        - Irrigation
        - Fertilizers
        - Plant diseases
        - Pests
        - General agriculture

        Rules:
        - Use simple language.
        - Give clear and practical answers.
        - Do not invent information.
        - If information is missing, ask for it.
        - If the question is not related to agriculture,
          politely say you are an agriculture-focused assistant."""),
    ("human", "{question}")
])


farming_chain = prompt | llm


def ask_farming_assistant(question: str):
    response = farming_chain.invoke(
        {"question": question}
    )
    return response.content


# -----------------------------
# FastAPI wrapper
# -----------------------------
# Exposes ask_farming_assistant() over HTTP so the KrishiSanchar
# frontend (web.js) can call it directly, the same way it calls the
# crop/fertilizer/yield/market/weather services.
#
# Run with:
#   uvicorn ai_assistant:app --port 8005

app = FastAPI(
    title="KrishiSanchar AI Farming Assistant API",
    description="Gemini-powered chat assistant for farming questions",
    version="1.0"
)

# Allow the KrishiSanchar frontend (served from a different origin/port)
# to call this API from the browser.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class AssistantQuery(BaseModel):
    question: str


@app.get("/")
def home():
    return {"message": "KrishiSanchar AI Farming Assistant API Running"}


@app.post("/ask")
def ask(query: AssistantQuery):
    question = (query.question or "").strip()

    if not question:
        raise HTTPException(status_code=400, detail="Question cannot be empty")

    try:
        answer = ask_farming_assistant(question)
    except Exception as e:
        raise HTTPException(
            status_code=502,
            detail={
                "error": "AI assistant failed to respond",
                "details": str(e),
            },
        )

    return {"question": question, "answer": answer}