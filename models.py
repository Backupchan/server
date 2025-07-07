"""
Application models. Read db.sql for explanation of what each field represents.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional
from datetime import datetime
import json
import nameformat

class BackupRecycleCriteria(str, Enum):
    NONE = "none"
    COUNT = "count"
    AGE = "age"

class BackupRecycleAction(str, Enum):
    DELETE = "delete"
    RECYCLE = "recycle"

class BackupType(str, Enum):
    SINGLE = "single"
    MULTI = "multi"

@dataclass
class BackupTarget:
    id: str
    name: str
    target_type: BackupType
    recycle_criteria: BackupRecycleCriteria
    recycle_value: Optional[int]
    recycle_action: BackupRecycleAction
    location: str
    name_template: str

@dataclass
class Backup:
    id: str
    target_id: str
    created_at: datetime
    manual: bool
    is_recycled: bool

    def pretty_created_at(self) -> str:
        return self.created_at.strftime("%B %d, %Y %H:%M")
