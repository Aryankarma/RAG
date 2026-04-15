import logging
import os

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.logging_config import setup_logging
from app.routes import rag

load_dotenv()
setup_logging()

logger = logging.getLogger(__name__)

app = FastAPI()
frontend_url = os.getenv("FRONTEND_PRODUCTION_URL") or "https://your-default.com"
logger.info("CORS allowed frontend URL: %s", frontend_url)

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