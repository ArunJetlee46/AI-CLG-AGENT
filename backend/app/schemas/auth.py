from pydantic import BaseModel, ConfigDict, Field


class LoginRequest(BaseModel):
    username: str
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    username: str
    role: str
    email: str = ""


class UserCreate(BaseModel):
    username: str = Field(min_length=3, max_length=64)
    password: str = Field(min_length=6, max_length=128)
    role: str = Field(pattern="^(student|lecturer|placement|admin)$")
    email: str = Field(default="", max_length=128)


class UserUpdate(BaseModel):
    role: str | None = Field(default=None, pattern="^(student|lecturer|placement|admin)$")
    is_active: bool | None = None
    password: str | None = Field(default=None, min_length=6, max_length=128)
