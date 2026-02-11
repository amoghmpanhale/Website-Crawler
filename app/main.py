from fastapi import FastAPI
from app.routes import auth_routes, collections, crawl

app = FastAPI()

app.include_router(auth_routes.router)
app.include_router(collections.router)
app.include_router(crawl.router)

@app.get("/")
async def root():
    return {"message": "RAG API is running"}