from typing import Literal
from pydantic import BaseModel, Field


class ProjectIn(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    path: str = ""


class ChatIn(BaseModel):
    project_id: str


class TurnIn(BaseModel):
    prompt: str = Field(min_length=1, max_length=16000)
    model: str | None = Field(default=None, min_length=1, max_length=160, pattern=r"^\S+$")
    local: bool = False
    external: bool = False
    mode: Literal["chat", "report"] = "chat"
    report_format: Literal["html", "pdf", "both"] = "html"


class SettingsIn(BaseModel):
    base_url: str
    model: str | None = None
    api_key: str | None = None


class LocalPathIn(BaseModel):
    path: str = Field(max_length=4096)
