from pydantic import BaseModel, model_validator
from pydantic.dataclasses import dataclass
from typing import Callable, Literal
from PIL import Image

""" 
Task class for defining quest tasks.
"""
@dataclass
class Task:
    id: str
    name: str
    description: str          
    hints: list[str]          # static, ordered nudge -> strong
    type: Literal["text", "math"] = "text"
    min_len: int = 1
    max_len: int | None = None
    no_spaces: bool = False
    max_distinct: int | None = None
    encode: Callable[[str], Image.Image] | None = None

    def eligible(self, word: str) -> bool:
        w = word.strip()
        if not (self.min_len <= len(w) <= (self.max_len or 999)):
            return False
        if self.no_spaces and " " in w:
            return False
        if self.max_distinct is not None and len(set(w.upper())) > self.max_distinct:
            return False
        return True

"""  
Request and response models for quest generation and selection.
"""

class CatalogEntry(BaseModel):
    name: str
    description: str
    type: Literal["text", "math"]

class QuestRequest(BaseModel):
    words: list[str]                    
    candidates: list[list[str]]         
    catalog: dict[str, CatalogEntry]
    type_preference: Literal["Any", "More text", "More math", "Balanced"] = "Any"
    user_message: str = ""  # raw wish, capped ~500 chars, context only

    @model_validator(mode="after")
    def _check_lengths(self):
        if not self.words or any(not w.strip() for w in self.words):
            raise ValueError("words must be non-empty")
        if len(self.candidates) != len(self.words):
            raise ValueError("candidates must align positionally to words")
        for ids in self.candidates:
            for tid in ids:
                if tid not in self.catalog:
                    raise ValueError(f"unknown task id: {tid!r}")
        return self

class Selection(BaseModel):
    task_id: str
    why: str = ""                       # cap ~120 chars post-parse

class QuestResponse(BaseModel):
    picks: list[Selection]              # must align positionally to words