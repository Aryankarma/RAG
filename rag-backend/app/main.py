from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from app.routes import rag
import os
from dotenv import load_dotenv

load_dotenv()

app = FastAPI() 
frontend_url = os.getenv("FRONTEND_PRODUCTION_URL") or "https://your-default.com"
print("CORS frontend URL:", frontend_url)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        frontend_url
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(rag.router, prefix="/rag")