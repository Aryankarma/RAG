from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from app.routes import rag
import os
from dotenv import load_dotenv

load_dotenv()

app = FastAPI() 

# Configure CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # Next.js default dev server
        "http://127.0.0.1:3000",  # Alternative localhost
        os.getenv("FRONTEND_PRODUCTION_URL"),
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

app.include_router(rag.router, prefix="/rag")