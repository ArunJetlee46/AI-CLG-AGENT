from pydantic import BaseModel, Field


class ApprovalDecision(BaseModel):
    decision: str = Field(pattern="^(approve|reject)$")
    comment: str = ""
