import datetime
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Boolean, Table
from sqlalchemy.orm import relationship
from app.database import Base

class User(Base):
    __tablename__ = "users"
    
    id = Column(String, primary_key=True)  # e.g., 'ada-77'
    name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    avatar = Column(String, default="")
    role = Column(String, default="Guest")  # "Admin", "Engineer", "Designer", "Guest"
    status = Column(String, default="offline")  # "online", "offline", "busy"
    github = Column(String, default="")
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    
    # Relationships
    chat_memberships = relationship("ChatMember", back_populates="user", cascade="all, delete-orphan")
    messages_sent = relationship("Message", back_populates="sender", cascade="all, delete-orphan")
    friend_requests_sent = relationship("FriendRequest", foreign_keys="FriendRequest.from_id", back_populates="sender", cascade="all, delete-orphan")
    friend_requests_received = relationship("FriendRequest", foreign_keys="FriendRequest.to_id", back_populates="receiver", cascade="all, delete-orphan")
    files_owned = relationship("FileItem", back_populates="owner", cascade="all, delete-orphan")


class Chat(Base):
    __tablename__ = "chats"
    
    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    type = Column(String, nullable=False)  # "direct", "group"
    avatar = Column(String, default="")
    last_message = Column(String, default="")
    last_message_time = Column(DateTime, default=datetime.datetime.utcnow)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    
    # Relationships
    memberships = relationship("ChatMember", back_populates="chat", cascade="all, delete-orphan")
    messages = relationship("Message", back_populates="chat", cascade="all, delete-orphan")
    files = relationship("FileItem", back_populates="chat", cascade="all, delete-orphan")


class ChatMember(Base):
    __tablename__ = "chat_members"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    chat_id = Column(String, ForeignKey("chats.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    role = Column(String, default="Member")  # "Admin", "Member"
    joined_at = Column(DateTime, default=datetime.datetime.utcnow)
    
    # Relationships
    chat = relationship("Chat", back_populates="memberships")
    user = relationship("User", back_populates="chat_memberships")


class Message(Base):
    __tablename__ = "messages"
    
    id = Column(String, primary_key=True)
    chat_id = Column(String, ForeignKey("chats.id", ondelete="CASCADE"), nullable=False)
    sender_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    content = Column(String, nullable=False)
    image = Column(String, default="")
    status = Column(String, default="sent")  # "sent", "delivered", "read"
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    
    # Relationships
    chat = relationship("Chat", back_populates="messages")
    sender = relationship("User", back_populates="messages_sent")


class FriendRequest(Base):
    __tablename__ = "friend_requests"
    
    id = Column(String, primary_key=True)
    from_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    to_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    status = Column(String, default="pending")  # "pending", "accepted", "rejected"
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    
    # Relationships
    sender = relationship("User", foreign_keys=[from_id], back_populates="friend_requests_sent")
    receiver = relationship("User", foreign_keys=[to_id], back_populates="friend_requests_received")


class FileItem(Base):
    __tablename__ = "files"
    
    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    type = Column(String, nullable=False)  # "folder", "image", "document", "archive", "code"
    size = Column(String, nullable=False)  # e.g., '1.1 MB'
    owner_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    chat_id = Column(String, ForeignKey("chats.id", ondelete="SET NULL"), nullable=True)
    url = Column(String, nullable=False)
    modified_at = Column(DateTime, default=datetime.datetime.utcnow)
    
    # Relationships
    owner = relationship("User", back_populates="files_owned")
    chat = relationship("Chat", back_populates="files")
