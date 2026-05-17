"""FastAPI dependencies — wire singletons stored on app.state into routes."""
from fastapi import Depends, Request

from ..core.config import Settings, get_settings
from ..controllers import AskController, AgentController, IndexController


def settings_dep() -> Settings:
    return get_settings()


def ask_controller_dep(request: Request) -> AskController:
    return request.app.state.ask_controller


def agent_controller_dep(request: Request) -> AgentController:
    return request.app.state.agent_controller


def index_controller_dep(request: Request) -> IndexController:
    return request.app.state.index_controller


SettingsDep = Depends(settings_dep)
AskCtrlDep = Depends(ask_controller_dep)
AgentCtrlDep = Depends(agent_controller_dep)
IndexCtrlDep = Depends(index_controller_dep)
