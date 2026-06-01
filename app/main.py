import os
import uuid
import datetime
from contextlib import asynccontextmanager
from typing import List, Optional

import socketio
from fastapi import FastAPI, Depends, HTTPException, status, UploadFile, File, Form, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import update, delete

from app.config import settings
from app.database import engine, Base, AsyncSessionLocal, get_db
from app.models import User, Chat, ChatMember, Message, FriendRequest, FileItem
from app.schemas import (
    UserCreate, UserLogin, UserAuthResponse, UserResponse,
    ChatSessionResponse, MessageResponse, MemberResponse,
    FriendRequestResponse, FriendRequestCreate, FriendRequestSuccessResponse,
    FriendRequestAcceptResponse, FileItemResponse, SuccessResponse
)
from app.auth import hash_password, verify_password, create_access_token, get_current_user, verify_token
from app.seed import seed_database

# Helper function to format datetime to user-friendly string
def format_time_readable(dt: datetime.datetime) -> str:
    now = datetime.datetime.utcnow()
    diff = now - dt
    if diff.days == 0:
        return dt.strftime("%I:%M %p").lstrip("0")
    elif diff.days == 1:
        return "Yesterday"
    else:
        return dt.strftime("%b %d, %Y")


# Lifespan Context Manager (replaces startup/shutdown events)
@asynccontextmanager
async def lifespan(app: FastAPI):
    # 1. Create tables in SQLite / PostgreSQL
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    # 2. Seed default data if database is empty
    async with AsyncSessionLocal() as session:
        await seed_database(session)
        
    yield
    # Shutdown logic (if any) can be placed here
    await engine.dispose()


# 1. Initialize FastAPI Application
app = FastAPI(
    title=settings.APP_NAME,
    description="Asynchronous FastAPI Backend with Socket.IO for Real-Time Cloud-Native Chat",
    version="1.0.0",
    lifespan=lifespan
)

# 2. Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 3. Initialize Socket.IO Server
sio = socketio.AsyncServer(
    async_mode='asgi',
    cors_allowed_origins='*',  # Allow all origins for real-time WebSocket handshake
    logger=False,
    engineio_logger=False
)
sio_asgi_app = socketio.ASGIApp(
    socketio_server=sio,
    other_asgi_app=app,
    socketio_path='/socket.io'
)


# ==========================================
# REST API ENDPOINTS
# ==========================================

@app.get("/")
async def root():
    return {
        "app": settings.APP_NAME,
        "status": "online",
        "realtime": "Socket.IO mounted",
        "docs": "/docs"
    }


# --- 1. AUTHENTICATION ENDPOINTS ---

@app.post("/api/auth/register", response_model=UserAuthResponse, status_code=status.HTTP_201_CREATED)
async def register(payload: UserCreate, db: AsyncSession = Depends(get_db)):
    # Check if username (id) or email already exists
    id_check = await db.execute(select(User).where(User.id == payload.userId))
    if id_check.scalars().first():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"message": "User ID already exists"}
        )
        
    email_check = await db.execute(select(User).where(User.email == payload.email))
    if email_check.scalars().first():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"message": "Email already registered"}
        )
        
    # Create new User
    # Default avatar based on Dicebear seed
    avatar_url = f"https://api.dicebear.com/7.x/adventurer/svg?seed={payload.userId}"
    new_user = User(
        id=payload.userId,
        name=payload.name,
        email=payload.email,
        password_hash=hash_password(payload.password),
        avatar=avatar_url,
        role="Guest",
        status="offline"
    )
    
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    
    # Generate token
    token = create_access_token(user_id=new_user.id, email=new_user.email, name=new_user.name)
    
    # Return user mapped properly
    return {
        "token": token,
        "user": {
            "id": new_user.id,
            "name": new_user.name,
            "email": new_user.email,
            "avatar": new_user.avatar
        }
    }


@app.post("/api/auth/login", response_model=UserAuthResponse)
async def login(payload: UserLogin, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == payload.email))
    user = result.scalars().first()
    
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"message": "Invalid email or password"}
        )
        
    # Generate token
    token = create_access_token(user_id=user.id, email=user.email, name=user.name)
    
    return {
        "token": token,
        "user": {
            "id": user.id,
            "name": user.name,
            "email": user.email,
            "avatar": user.avatar or ""
        }
    }


# --- 2. CHATS & ROOMS ENDPOINTS ---

@app.get("/api/chats", response_model=List[ChatSessionResponse])
async def get_chats(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    # 1. Find all chats this user is a member of
    memberships_result = await db.execute(
        select(ChatMember).where(ChatMember.user_id == current_user.id)
    )
    memberships = memberships_result.scalars().all()
    
    chat_sessions = []
    for membership in memberships:
        chat_result = await db.execute(
            select(Chat).where(Chat.id == membership.chat_id)
        )
        chat = chat_result.scalars().first()
        if not chat:
            continue
            
        chat_name = chat.name
        chat_avatar = chat.avatar or ""
        is_online = False
        
        # For direct chat, determine name, avatar, and online status from the other user
        if chat.type == "direct":
            other_member_result = await db.execute(
                select(ChatMember).where(
                    ChatMember.chat_id == chat.id,
                    ChatMember.user_id != current_user.id
                )
            )
            other_member = other_member_result.scalars().first()
            if other_member:
                other_user_result = await db.execute(
                    select(User).where(User.id == other_member.user_id)
                )
                other_user = other_user_result.scalars().first()
                if other_user:
                    chat_name = other_user.name
                    chat_avatar = other_user.avatar or ""
                    is_online = (other_user.status == "online")
        else:
            # Group chats are online by default
            is_online = True
            
        # Count unread messages (simplistic: messages where status != "read" and sender != current_user)
        unread_result = await db.execute(
            select(Message).where(
                Message.chat_id == chat.id,
                Message.sender_id != current_user.id,
                Message.status != "read"
            )
        )
        unread_count = len(unread_result.scalars().all())
        
        # Format last message details
        last_msg_txt = chat.last_message or ""
        # If group, prepend sender name to match UI mock if not already present
        if chat.type == "group" and chat.last_message and ":" not in chat.last_message:
            # Find latest message in group
            latest_msg_res = await db.execute(
                select(Message).where(Message.chat_id == chat.id).order_by(Message.created_at.desc()).limit(1)
            )
            latest_msg = latest_msg_res.scalars().first()
            if latest_msg:
                sender_res = await db.execute(select(User).where(User.id == latest_msg.sender_id))
                sender = sender_res.scalars().first()
                if sender:
                    last_msg_txt = f"{sender.name}: {latest_msg.content}"
        
        chat_sessions.append({
            "id": chat.id,
            "name": chat_name,
            "type": chat.type,
            "avatar": chat_avatar,
            "color": "bg-indigo-500" if chat.type == "group" else "bg-emerald-500",
            "lastMessage": last_msg_txt,
            "time": format_time_readable(chat.last_message_time) if chat.last_message_time else "Just now",
            "unreadCount": unread_count,
            "online": is_online
        })
        
    # Sort chats by latest message time descending
    chat_sessions.sort(key=lambda x: x["time"], reverse=True)
    return chat_sessions


@app.get("/api/chats/{chat_id}/messages", response_model=List[MessageResponse])
async def get_messages(chat_id: str, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    # Verify user is a member of this chat
    membership_res = await db.execute(
        select(ChatMember).where(ChatMember.chat_id == chat_id, ChatMember.user_id == current_user.id)
    )
    if not membership_res.scalars().first():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"message": "You are not a member of this chat"}
        )
        
    # Fetch messages
    messages_res = await db.execute(
        select(Message).where(Message.chat_id == chat_id).order_by(Message.created_at.asc())
    )
    messages = messages_res.scalars().all()
    
    response = []
    for msg in messages:
        sender_res = await db.execute(select(User).where(User.id == msg.sender_id))
        sender = sender_res.scalars().first()
        sender_name = sender.name if sender else "Unknown User"
        sender_avatar = sender.avatar if sender else ""
        
        response.append({
            "id": msg.id,
            "senderId": msg.sender_id,
            "senderName": sender_name,
            "senderAvatar": sender_avatar,
            "senderColor": "bg-indigo-500",
            "time": format_time_readable(msg.created_at),
            "content": msg.content,
            "image": msg.image or "",
            "status": msg.status,
            "isSelf": (msg.sender_id == current_user.id)
        })
        
    return response


# --- 3. MEMBERS ENDPOINTS ---

@app.get("/api/members", response_model=List[MemberResponse])
async def get_members(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    # Returns all users registered in the system
    result = await db.execute(select(User).order_by(User.name.asc()))
    users = result.scalars().all()
    
    members = []
    for u in users:
        members.append({
            "id": u.id,
            "name": u.name,
            "role": u.role or "Guest",
            "status": u.status or "offline",
            "avatar": u.avatar or "",
            "color": "bg-rose-500" if u.role == "Admin" else "bg-emerald-500",
            "email": u.email,
            "github": u.github or ""
        })
        
    return members


# --- 4. FRIEND REQUEST ENDPOINTS ---

@app.get("/api/friend-requests", response_model=List[FriendRequestResponse])
async def get_friend_requests(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    # Fetch pending requests directed to the current user
    result = await db.execute(
        select(FriendRequest).where(
            FriendRequest.to_id == current_user.id,
            FriendRequest.status == "pending"
        )
    )
    requests = result.scalars().all()
    
    response = []
    for r in requests:
        sender_res = await db.execute(select(User).where(User.id == r.from_id))
        sender = sender_res.scalars().first()
        sender_name = sender.name if sender else "Unknown User"
        
        response.append({
            "id": r.id,
            "fromId": r.from_id,
            "fromName": sender_name
        })
        
    return response


@app.post("/api/friend-requests", response_model=FriendRequestSuccessResponse)
async def send_friend_request(payload: FriendRequestCreate, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    to_id = payload.to
    
    # Check if target user exists
    target_res = await db.execute(select(User).where(User.id == to_id))
    target = target_res.scalars().first()
    if not target:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"message": "User ID not found. Please check the ID and try again."}
        )
        
    # Check if sending request to self
    if to_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"message": "Cannot send friend request to yourself"}
        )
        
    # Check if request already pending
    existing_res = await db.execute(
        select(FriendRequest).where(
            FriendRequest.from_id == current_user.id,
            FriendRequest.to_id == to_id,
            FriendRequest.status == "pending"
        )
    )
    existing = existing_res.scalars().first()
    if existing:
        return {
            "success": True,
            "request": {
                "id": existing.id,
                "fromId": existing.from_id,
                "fromName": current_user.name,
                "toId": existing.to_id,
                "status": existing.status
            }
        }
        
    # Create request
    new_req = FriendRequest(
        id=f"req-{uuid.uuid4().hex[:8]}",
        from_id=current_user.id,
        to_id=to_id,
        status="pending"
    )
    db.add(new_req)
    await db.commit()
    
    # Emit Real-time Socket.IO notification if recipient is connected
    await sio.emit(
        "friendRequestReceived",
        {
            "id": new_req.id,
            "fromId": current_user.id,
            "fromName": current_user.name
        },
        room=f"user_{to_id}"
    )
    
    return {
        "success": True,
        "request": {
            "id": new_req.id,
            "fromId": current_user.id,
            "fromName": current_user.name,
            "toId": to_id,
            "status": "pending"
        }
    }


@app.post("/api/friend-requests/{request_id}/accept", response_model=FriendRequestAcceptResponse)
async def accept_friend_request(request_id: str, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(FriendRequest).where(FriendRequest.id == request_id))
    req = result.scalars().first()
    
    if not req:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"message": "Friend request not found"}
        )
        
    if req.to_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"message": "You do not have permission to accept this request"}
        )
        
    req.status = "accepted"
    
    # Create Direct Chat between the two users
    chat_id = f"direct-{uuid.uuid4().hex[:8]}"
    sender_res = await db.execute(select(User).where(User.id == req.from_id))
    sender = sender_res.scalars().first()
    sender_name = sender.name if sender else "Unknown User"
    
    direct_chat = Chat(
        id=chat_id,
        name=sender_name,
        type="direct",
        avatar=sender.avatar if sender else "",
        last_message="Say hi!",
        last_message_time=datetime.datetime.utcnow()
    )
    
    db.add(direct_chat)
    await db.flush()
    
    # Add ChatMembers
    member_from = ChatMember(chat_id=chat_id, user_id=req.from_id, role="Member")
    member_to = ChatMember(chat_id=chat_id, user_id=current_user.id, role="Member")
    db.add_all([member_from, member_to])
    
    # Create a Welcome Message
    welcome_msg = Message(
        id=f"msg-{uuid.uuid4().hex[:8]}",
        chat_id=chat_id,
        sender_id=req.from_id,
        content="Say hi!",
        status="delivered"
    )
    db.add(welcome_msg)
    await db.commit()
    
    chat_data = {
        "id": chat_id,
        "name": sender_name,
        "type": "direct",
        "avatar": sender.avatar if sender else "",
        "color": "bg-emerald-500",
        "lastMessage": "Say hi!",
        "time": "Just now",
        "unreadCount": 0,
        "online": (sender.status == "online") if sender else False
    }
    
    # Emit Socket.IO friendRequestAccepted real-time event to the sender
    chat_data_for_sender = dict(chat_data)
    chat_data_for_sender["name"] = current_user.name
    chat_data_for_sender["avatar"] = current_user.avatar
    chat_data_for_sender["online"] = (current_user.status == "online")
    
    await sio.emit(
        "friendRequestAccepted",
        {
            "requestId": request_id,
            "chat": chat_data_for_sender
        },
        room=f"user_{req.from_id}"
    )
    
    return {
        "success": True,
        "chat": chat_data
    }


@app.post("/api/friend-requests/{request_id}/reject", response_model=SuccessResponse)
async def reject_friend_request(request_id: str, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(FriendRequest).where(FriendRequest.id == request_id))
    req = result.scalars().first()
    
    if not req:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"message": "Friend request not found"}
        )
        
    if req.to_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"message": "You do not have permission to reject this request"}
        )
        
    req.status = "rejected"
    await db.commit()
    
    return {"success": True}


# --- 5. USER LOOKUP ENDPOINTS ---

@app.get("/api/users/{user_id}", response_model=UserResponse)
async def lookup_user(user_id: str, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalars().first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"message": "User ID not found. Please check the ID and try again."}
        )
        
    return {
        "id": user.id,
        "name": user.name,
        "email": user.email,
        "avatar": user.avatar or ""
    }


# --- 6. FILE MANAGEMENT ENDPOINTS ---

@app.get("/api/files", response_model=List[FileItemResponse])
async def get_files(
    chatId: Optional[str] = None,
    q: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    query = select(FileItem)
    
    if chatId:
        query = query.where(FileItem.chat_id == chatId)
    if q:
        query = query.where(FileItem.name.icontains(q))
        
    result = await db.execute(query.order_by(FileItem.modified_at.desc()))
    files = result.scalars().all()
    
    response = []
    for f in files:
        owner_res = await db.execute(select(User).where(User.id == f.owner_id))
        owner = owner_res.scalars().first()
        owner_name = owner.name if owner else "System"
        
        response.append({
            "id": f.id,
            "name": f.name,
            "type": f.type,
            "size": f.size,
            "modified": format_time_readable(f.modified_at),
            "owner": owner_name
        })
        
    return response


@app.post("/api/files", response_model=FileItemResponse, status_code=status.HTTP_201_CREATED)
async def upload_file(
    file: UploadFile = File(...),
    chatId: Optional[str] = Form(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    # Save the file locally in uploads folder
    file_id = f"file-{uuid.uuid4().hex[:8]}"
    file_ext = os.path.splitext(file.filename)[1]
    saved_filename = f"{file_id}{file_ext}"
    saved_filepath = os.path.join(settings.UPLOAD_DIR, saved_filename)
    
    with open(saved_filepath, "wb") as f_out:
        content = await file.read()
        f_out.write(content)
        
    # Calculate file size
    size_bytes = len(content)
    if size_bytes < 1024:
        size_str = f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        size_str = f"{size_bytes / 1024:.1f} KB"
    else:
        size_str = f"{size_bytes / (1024 * 1024):.1f} MB"
        
    # Determine type
    mime_type = file.content_type or ""
    if mime_type.startswith("image/"):
        file_type = "image"
    elif mime_type.startswith("text/") or file_ext in [".py", ".ts", ".js", ".tsx", ".html", ".css"]:
        file_type = "code"
    elif file_ext in [".zip", ".tar", ".gz", ".rar", ".7z"]:
        file_type = "archive"
    elif file_ext in [".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx", ".txt"]:
        file_type = "document"
    else:
        file_type = "document"
        
    url = f"http://localhost:5000/api/files/{file_id}/download"
    
    # Store in database
    new_file = FileItem(
        id=file_id,
        name=file.filename,
        type=file_type,
        size=size_str,
        owner_id=current_user.id,
        chat_id=chatId,
        url=url
    )
    db.add(new_file)
    await db.commit()
    await db.refresh(new_file)
    
    return {
        "id": new_file.id,
        "name": new_file.name,
        "type": new_file.type,
        "size": new_file.size,
        "modified": "Just now",
        "owner": current_user.name
    }


@app.get("/api/files/{file_id}/download")
async def download_file(file_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(FileItem).where(FileItem.id == file_id))
    file_item = result.scalars().first()
    
    if not file_item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"message": "File not found"}
        )
        
    # Locate actual file
    file_ext = os.path.splitext(file_item.name)[1]
    saved_filename = f"{file_item.id}{file_ext}"
    saved_filepath = os.path.join(settings.UPLOAD_DIR, saved_filename)
    
    if not os.path.exists(saved_filepath):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"message": "File binary missing from disk"}
        )
        
    return FileResponse(
        path=saved_filepath,
        filename=file_item.name,
        media_type="application/octet-stream"
    )


# ==========================================
# SOCKET.IO REAL-TIME EVENT HANDLERS
# ==========================================

@sio.event
async def connect(sid, environ, auth=None):
    if not auth or 'token' not in auth:
        print(f"WS connection rejected: Missing token from sid {sid}")
        raise socketio.exceptions.ConnectionRefusedError('Authentication failed')
        
    token = auth['token']
    payload = verify_token(token)
    
    if not payload:
        print(f"WS connection rejected: Invalid token from sid {sid}")
        raise socketio.exceptions.ConnectionRefusedError('Invalid token')
        
    user_id = payload.get("sub")
    user_name = payload.get("name")
    
    # Save user_id & name in socket session
    await sio.save_session(sid, {'user_id': user_id, 'user_name': user_name})
    
    # Update status to online in database
    async with AsyncSessionLocal() as db:
        await db.execute(
            update(User).where(User.id == user_id).values(status="online")
        )
        await db.commit()
        
    # Enter their private room for single-user notifications
    await sio.enter_room(sid, f"user_{user_id}")
    
    # Broadcast presence status update to everyone
    await sio.emit("memberStatusUpdate", {"id": user_id, "status": "online"})
    print(f"WS Client connected: User {user_name} ({user_id}) on sid {sid}")


@sio.event
async def disconnect(sid):
    session = await sio.get_session(sid)
    if not session:
        return
        
    user_id = session.get('user_id')
    user_name = session.get('user_name')
    
    if user_id:
        # Update user status to offline in database
        async with AsyncSessionLocal() as db:
            await db.execute(
                update(User).where(User.id == user_id).values(status="offline")
            )
            await db.commit()
            
        # Broadcast presence status update to everyone
        await sio.emit("memberStatusUpdate", {"id": user_id, "status": "offline"})
        print(f"WS Client disconnected: User {user_name} ({user_id})")


@sio.event
async def joinChat(sid, data):
    chat_id = data.get("chatId")
    if chat_id:
        await sio.enter_room(sid, f"chat_{chat_id}")
        print(f"WS Client sid {sid} joined chat room: chat_{chat_id}")


@sio.event
async def leaveChat(sid, data):
    chat_id = data.get("chatId")
    if chat_id:
        await sio.leave_room(sid, f"chat_{chat_id}")
        print(f"WS Client sid {sid} left chat room: chat_{chat_id}")


@sio.event
async def sendMessage(sid, data):
    session = await sio.get_session(sid)
    if not session:
        return
        
    sender_id = session.get('user_id')
    sender_name = session.get('user_name')
    
    chat_id = data.get("chatId")
    content = data.get("content")
    
    if not chat_id or not content:
        return
        
    async with AsyncSessionLocal() as db:
        # 1. Fetch sender profile
        sender_res = await db.execute(select(User).where(User.id == sender_id))
        sender = sender_res.scalars().first()
        sender_avatar = sender.avatar if sender else ""
        
        # 2. Save Message to Database
        msg_id = f"msg-{uuid.uuid4().hex[:8]}"
        new_msg = Message(
            id=msg_id,
            chat_id=chat_id,
            sender_id=sender_id,
            content=content,
            status="delivered"
        )
        db.add(new_msg)
        
        # 3. Update Chat Last Message
        chat_last_msg = f"{sender_name}: {content}"
        await db.execute(
            update(Chat).where(Chat.id == chat_id).values(
                last_message=chat_last_msg,
                last_message_time=datetime.datetime.utcnow()
            )
        )
        await db.commit()
        
        # 4. Construct payload for client
        # To match direct/group view, send isSelf dynamic calculations
        payload_received = {
            "id": msg_id,
            "senderId": sender_id,
            "senderName": sender_name,
            "senderAvatar": sender_avatar,
            "senderColor": "bg-indigo-500",
            "time": "Just now",
            "content": content,
            "image": "",
            "status": "delivered",
            "isSelf": False  # Handled by frontend based on user.id
        }
        
        # 5. Broadcast message to all users in chat room
        await sio.emit("receiveMessage", payload_received, room=f"chat_{chat_id}")
        
        # 6. Notify sidebar updates in real-time
        # Query all members of this chat
        members_res = await db.execute(
            select(ChatMember).where(ChatMember.chat_id == chat_id)
        )
        members = members_res.scalars().all()
        
        for member in members:
            # Format time string for sidebar
            sidebar_time = "Just now"
            
            # Count unread messages for that member
            unread_count = 0
            if member.user_id != sender_id:
                unread_res = await db.execute(
                    select(Message).where(
                        Message.chat_id == chat_id,
                        Message.sender_id != member.user_id,
                        Message.status != "read"
                    )
                )
                unread_count = len(unread_res.scalars().all())
                
            chat_update_payload = {
                "id": chat_id,
                "lastMessage": chat_last_msg,
                "time": sidebar_time,
                "unreadCount": unread_count
            }
            # Emit to each member's private room
            await sio.emit("chatUpdated", chat_update_payload, room=f"user_{member.user_id}")
            
    print(f"WS Broadcasted sendMessage from User {sender_name} to chat {chat_id}")
