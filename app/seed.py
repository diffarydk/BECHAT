import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.auth import hash_password
from app.models import User, Chat, ChatMember, Message, FriendRequest, FileItem

async def seed_database(db: AsyncSession):
    # Check if we already have users
    result = await db.execute(select(User))
    if result.scalars().first():
        print("Database already seeded. Skipping...")
        return
        
    print("Database is empty. Starting seed process...")
    
    # 1. Create Users
    users_data = [
        {
            "id": "ada-77",
            "name": "Ada Lovelace",
            "email": "ada@example.com",
            "password_hash": hash_password("Secret123"),
            "role": "Admin",
            "status": "online",
            "avatar": "https://api.dicebear.com/7.x/adventurer/svg?seed=Ada",
            "github": "adalovelace"
        },
        {
            "id": "bob-99",
            "name": "Bob Engineer",
            "email": "bob@example.com",
            "password_hash": hash_password("Secret123"),
            "role": "Engineer",
            "status": "offline",
            "avatar": "https://api.dicebear.com/7.x/adventurer/svg?seed=Bob",
            "github": "bobengineer"
        },
        {
            "id": "elena",
            "name": "Elena Rostova",
            "email": "elena@example.com",
            "password_hash": hash_password("Secret123"),
            "role": "Admin",
            "status": "online",
            "avatar": "https://api.dicebear.com/7.x/adventurer/svg?seed=Elena",
            "github": "erostova"
        },
        {
            "id": "marcus",
            "name": "Marcus Chen",
            "email": "marcus@example.com",
            "password_hash": hash_password("Secret123"),
            "role": "Engineer",
            "status": "online",
            "avatar": "https://api.dicebear.com/7.x/adventurer/svg?seed=Marcus",
            "github": "mchen"
        }
    ]
    
    users = []
    for u_data in users_data:
        user = User(**u_data)
        db.add(user)
        users.append(user)
        
    # Flush to ensure users exist for foreign keys
    await db.flush()
    
    # 2. Create Chats
    # Group chat: Engineering Team
    group_chat = Chat(
        id="c1",
        name="Engineering Team",
        type="group",
        avatar="https://api.dicebear.com/7.x/identicon/svg?seed=Engineering",
        last_message="Welcome to Engineering Team",
        last_message_time=datetime.datetime.utcnow() - datetime.timedelta(minutes=5)
    )
    db.add(group_chat)
    
    # Direct chat: Elena Rostova (with Ada)
    direct_chat = Chat(
        id="u2",
        name="Elena Rostova",
        type="direct",
        avatar="https://api.dicebear.com/7.x/adventurer/svg?seed=Elena",
        last_message="Verification complete!",
        last_message_time=datetime.datetime.utcnow() - datetime.timedelta(minutes=10)
    )
    db.add(direct_chat)
    
    await db.flush()
    
    # 3. Add Members to Group Chat (c1)
    # Join Ada, Bob, Elena, Marcus to c1
    for u in users:
        role = "Admin" if u.id in ["ada-77", "elena"] else "Member"
        member = ChatMember(chat_id="c1", user_id=u.id, role=role)
        db.add(member)
        
    # 4. Add Members to Direct Chat (u2)
    # Join Ada and Elena to u2
    member_ada = ChatMember(chat_id="u2", user_id="ada-77", role="Member")
    member_elena = ChatMember(chat_id="u2", user_id="elena", role="Member")
    db.add(member_ada)
    db.add(member_elena)
    
    await db.flush()
    
    # 5. Seed Messages
    # Group messages
    m1 = Message(
        id="msg-1",
        chat_id="c1",
        sender_id="elena",
        content="Can someone verify the glow intensity?",
        status="read",
        created_at=datetime.datetime.utcnow() - datetime.timedelta(minutes=20)
    )
    m2 = Message(
        id="msg-2",
        chat_id="c1",
        sender_id="marcus",
        content="Pushing the fix now.",
        status="read",
        created_at=datetime.datetime.utcnow() - datetime.timedelta(minutes=15)
    )
    m3 = Message(
        id="msg-3",
        chat_id="c1",
        sender_id="ada-77",
        content="Welcome to Engineering Team!",
        status="read",
        created_at=datetime.datetime.utcnow() - datetime.timedelta(minutes=5)
    )
    db.add_all([m1, m2, m3])
    
    # Direct messages in u2
    dm1 = Message(
        id="msg-4",
        chat_id="u2",
        sender_id="elena",
        content="Verification complete!",
        status="read",
        created_at=datetime.datetime.utcnow() - datetime.timedelta(minutes=10)
    )
    db.add(dm1)
    
    # 6. Seed Friend Requests
    # Request from bob-99 to ada-77
    req1 = FriendRequest(
        id="req-1",
        from_id="bob-99",
        to_id="ada-77",
        status="pending",
        created_at=datetime.datetime.utcnow() - datetime.timedelta(hours=1)
    )
    db.add(req1)
    
    # 7. Seed Files
    f1 = FileItem(
        id="file-1",
        name="api_spec_v1.4.pdf",
        type="document",
        size="1.1 MB",
        owner_id="marcus",
        chat_id="c1",
        url="http://localhost:5000/api/files/file-1/download",
        modified_at=datetime.datetime.utcnow() - datetime.timedelta(hours=5)
    )
    f2 = FileItem(
        id="file-2",
        name="hero_background_v2.png",
        type="image",
        size="4.2 MB",
        owner_id="ada-77",
        chat_id="c1",
        url="http://localhost:5000/api/files/file-2/download",
        modified_at=datetime.datetime.utcnow() - datetime.timedelta(minutes=30)
    )
    db.add_all([f1, f2])
    
    await db.commit()
    print("Database seeding completed successfully!")
