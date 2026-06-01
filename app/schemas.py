from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List

# User Schemas
class UserBase(BaseModel):
    email: EmailStr
    name: str

class UserCreate(BaseModel):
    userId: str = Field(..., min_length=2, max_length=50)
    name: str = Field(..., min_length=2, max_length=100)
    email: EmailStr
    password: str = Field(..., min_length=6)

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserResponse(BaseModel):
    id: str
    name: str
    email: str
    avatar: str = ""

    class Config:
        from_attributes = True

class UserAuthResponse(BaseModel):
    token: str
    user: UserResponse


# Member Schemas (for Member directory and sidebars)
class MemberResponse(BaseModel):
    id: str
    name: str
    role: str
    status: str
    avatar: str = ""
    color: Optional[str] = ""
    email: Optional[str] = ""
    github: Optional[str] = ""

    class Config:
        from_attributes = True


# Chat Schemas
class ChatSessionResponse(BaseModel):
    id: str
    name: str
    type: str  # "direct", "group"
    avatar: str = ""
    color: Optional[str] = ""
    lastMessage: str = ""
    time: str = ""
    unreadCount: int = 0
    online: bool = False

    class Config:
        from_attributes = True


# Message Schemas
class MessageCreate(BaseModel):
    content: str

class MessageResponse(BaseModel):
    id: str
    senderId: str
    senderName: str
    senderAvatar: str = ""
    senderColor: Optional[str] = ""
    time: str = ""
    content: str
    image: Optional[str] = ""
    status: str = "sent"  # "sent", "delivered", "read"
    isSelf: bool = False

    class Config:
        from_attributes = True


# Friend Request Schemas
class FriendRequestCreate(BaseModel):
    to: str

class FriendRequestResponse(BaseModel):
    id: str
    fromId: str
    fromName: str

    class Config:
        from_attributes = True

class FriendRequestDetails(BaseModel):
    id: str
    fromId: str
    fromName: str
    toId: str
    status: str

class FriendRequestSuccessResponse(BaseModel):
    success: bool
    request: FriendRequestDetails

class FriendRequestAcceptResponse(BaseModel):
    success: bool
    chat: ChatSessionResponse


# File Schemas
class FileItemResponse(BaseModel):
    id: str
    name: str
    type: str  # "folder", "image", "document", "archive", "code"
    size: str
    modified: str
    owner: str

    class Config:
        from_attributes = True


# Generic Success Response
class SuccessResponse(BaseModel):
    success: bool
