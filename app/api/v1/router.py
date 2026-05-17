from fastapi import APIRouter

from .routes import agent, ask, health, index

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(ask.router, tags=["ask"])
api_router.include_router(agent.router, tags=["agent"])
api_router.include_router(index.router, tags=["index"])
