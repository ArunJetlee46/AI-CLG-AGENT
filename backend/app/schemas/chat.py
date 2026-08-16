from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    session_id: str | None = Field(default=None, max_length=64, description="Chat thread id; None uses the default thread.")


class ChatResponse(BaseModel):
    intent: str
    agent: str
    answer: str
    citations: list[str] = []
    requires_approval: bool = False
    approval_id: str | None = None
    decision_card_id: str | None = None
    provider: str = ""
    model: str = ""
