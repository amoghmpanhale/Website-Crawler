from fastapi import FastAPI
from app.routes import auth_routes, collections

app = FastAPI()

app.include_router(auth_routes.router)
app.include_router(collections.router)
