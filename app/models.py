from __future__ import annotations
from typing import Literal, Optional, Dict, List
from pydantic import BaseModel, Field
from uuid import uuid4

DeckValue = Literal["0","1","2","3","5","8","13","20","40","100","?","coffee"]

class Player(BaseModel):
    id: str = Field(default_factory=lambda: uuid4().hex)
    nickname: str

class Story(BaseModel):
    id: str
    title: str
    description: Optional[str] = ""
    priority: Optional[str] = None
    acceptanceCriteria: Optional[List[str]] = None
    status: Literal["pending","in_progress","validated","unestimated"] = "pending"
    finalEstimate: Optional[str] = None
    rounds: List[Dict] = Field(default_factory=list)

class Backlog(BaseModel):
    project: str = "Planning Poker"
    version: int = 1
    stories: List[Story] = Field(default_factory=list)
    currentIndex: int = 0

class SessionRules(BaseModel):
    deck: List[DeckValue] = ["0","1","2","3","5","8","13","20","40","100","?","coffee"]
    firstRound: Literal["unanimity"] = "unanimity"

class Session(BaseModel):
    id: str = Field(default_factory=lambda: uuid4().hex[:6].upper())
    name: str
    mode: Literal["strict","median","mean","abs_majority","rel_majority"] = "strict"
    owner: str | None = None          # <- AJOUT
    players: List[Player] = Field(default_factory=list)
    rules: SessionRules = Field(default_factory=SessionRules)
    is_closed: bool = False
    backlog: Backlog = Field(default_factory=Backlog)

# DTOs (entrées API)
class CreateSessionIn(BaseModel):
    name: str = Field(description="Nom de la session")
    mode: Literal["strict","median","mean","abs_majority","rel_majority"] = Field("strict", description="Mode de jeu choisi")
    owner: str | None = None  # pseudo/identité du facilitateur (créateur), optionnel
    model_config = {
        "json_schema_extra": {
            "example": {
                "name": "Sprint 13",
                "mode": "median"
            }
        }
    }

class JoinSessionIn(BaseModel):
    nickname: str

class UploadBacklogIn(BaseModel):
    project: Optional[str] = "Planning Poker"
    version: int = 1
    stories: List[Story]

class SelectStoryIn(BaseModel):
    storyId: str
