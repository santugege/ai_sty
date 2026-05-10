from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class RegisterRequest(BaseModel):
    email: str
    username: str
    password: str


class LoginRequest(BaseModel):
    email: str
    password: str


class AdminUserUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: str | None = None
    username: str | None = None
    isActive: bool | None = None


class AdminPasswordResetRequest(BaseModel):
    password: str


class UserDto(BaseModel):
    id: str
    userId: str
    email: str
    username: str
    isAdmin: bool
    isActive: bool
    createdAt: str
    updatedAt: str


class AuthEnvelope(BaseModel):
    user: UserDto | None


class UserListEnvelope(BaseModel):
    users: list[UserDto]
