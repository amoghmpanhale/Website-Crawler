import time
from fastapi import FastAPI
from app.logging_config import logger
from crawl4ai.utils import configure_windows_event_loop
from app.routes import auth_routes
from app.routes import collections
from app.routes import crawl

# crawl4ai function that configures windows to use ProactorEventLoop which is required for async subprocesses used in 
# crawling. This should be called at the very start of the program before any async code runs. Otherwise it will use 
# SelectorEventLoop which does not support subprocesses and will cause the crawler to fail on Window.
configure_windows_event_loop()

app = FastAPI()

app.include_router(auth_routes.router)
logger.info("auth_routes loaded.")

app.include_router(collections.router)
logger.info("collections loaded.")

app.include_router(crawl.router)
logger.info(f"crawl loaded.")

@app.get("/")
async def root():
    logger.info("Root endpoint hit")
    return {"message": "RAG API is running"}