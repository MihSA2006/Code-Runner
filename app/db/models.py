from dataclasses import dataclass
from typing import Optional

@dataclass
class Execution:
    token: str
    status: str          # pending | running | done | error
    language: str
    output: Optional[str] = None
    error: Optional[str] = None
    created_at: Optional[float] = None
    completed_at: Optional[float] = None

    def to_dict(self):
        return {
            "token": self.token,
            "status": self.status,
            "language": self.language,
            "output": self.output,
            "error": self.error,
            "created_at": self.created_at,
            "completed_at": self.completed_at,
        }
