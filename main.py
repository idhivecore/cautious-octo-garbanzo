# backend/main.py
import uuid
import os
from datetime import datetime, timedelta
from typing import Dict, List

from fastapi import Body, FastAPI, HTTPException, UploadFile, File, Depends, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, Integer, String, Boolean, ForeignKey, DateTime, or_
from sqlalchemy.orm import sessionmaker, declarative_base, relationship, Session

# Set up FastAPI
app = FastAPI()

# Allow frontend access (assumed to be running at localhost:3000)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory store for active WebSocket connections by channel
active_connections: Dict[int, List[WebSocket]] = {}

# Directory for uploaded images
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")

# SQLite Database Setup
DATABASE_URL = "sqlite:///./database.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Online threshold time
ONLINE_THRESHOLD = timedelta(minutes=5)

# ---------------------------
# Database Models
# ---------------------------
class Token(Base):
    __tablename__ = "tokens"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    token = Column(String, unique=True, index=True)

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    display_name = Column(String)
    password = Column(String)
    profile_picture = Column(String, nullable=True)  # URL for the profile image
    last_active = Column(DateTime, nullable=True)
    online = Column(Boolean, default=False)
    
    alternates = relationship("AlternateProfile", back_populates="owner")

class AlternateProfile(Base):
    __tablename__ = "alternate_profiles"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    name = Column(String)
    icon = Column(String, nullable=True)  # URL for the alternate profile icon
    
    owner = relationship("User", back_populates="alternates")

class Server(Base):
    __tablename__ = "servers"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)

    channels = relationship("Channel", back_populates="server")

class Channel(Base):
    __tablename__ = "channels"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    server_id = Column(Integer, ForeignKey("servers.id"))
    
    server = relationship("Server", back_populates="channels")
    messages = relationship("Message", back_populates="channel")

class Message(Base):
    __tablename__ = "messages"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))  # sender's ID
    server_id = Column(Integer, ForeignKey("servers.id"))
    channel_id = Column(Integer, ForeignKey("channels.id"))
    content = Column(String)
    timestamp = Column(DateTime, default=datetime.utcnow)
    is_action = Column(Boolean, default=False)  # For roleplay actions
    is_edited = Column(Boolean, default=False)  # For edited messages
    alternate_id = Column(Integer, default=0)
    
    channel = relationship("Channel", back_populates="messages")

# New model for private messages
class PrivateMessage(Base):
    __tablename__ = "private_messages"
    
    id = Column(Integer, primary_key=True, index=True)
    sender_id = Column(Integer, ForeignKey("users.id"))
    receiver_id = Column(Integer, ForeignKey("users.id"))
    content = Column(String)
    timestamp = Column(DateTime, default=datetime.utcnow)
    is_edited = Column(Boolean, default=False)
    
    sender = relationship("User", foreign_keys=[sender_id])
    receiver = relationship("User", foreign_keys=[receiver_id])

# Create tables on startup
Base.metadata.create_all(bind=engine)

# ---------------------------
# Utility Functions
# ---------------------------
def get_db():
    """Dependency for database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def update_user_activity(username: str, db: Session):
    """Update a user's last_active timestamp and online status."""
    user = db.query(User).filter(User.username == username).first()
    if user:
        user.last_active = datetime.utcnow()
        user.online = True
        db.commit()

def save_uploaded_file(file: UploadFile) -> str:
    """Save an uploaded file and return its path."""
    file_location = os.path.join(UPLOAD_DIR, file.filename)
    with open(file_location, "wb") as f:
        f.write(file.file.read())
    return f"/uploads/{file.filename}"

def broadcast_to_channel(channel_id: int, payload: dict):
    """Broadcast a payload to all active WebSocket connections for the channel."""
    if channel_id in active_connections:
        for connection in active_connections[channel_id]:
            try:
                # Use asyncio.create_task if you want to schedule without waiting
                import asyncio
                asyncio.create_task(connection.send_json(payload))
            except Exception:
                continue

# ---------------------------
# API Endpoints
# ---------------------------
class RegisterRequest(BaseModel):
    username: str
    password: str
    display_name: str
    
class TokenRequest(BaseModel):
    token: str

class CreateServerRequest(BaseModel):
    name: str

class CreateChannelRequest(BaseModel):
    server_id: int
    name: str

# Updated SendMessageRequest now accepts alternate_id and is_action flag
class SendMessageRequest(BaseModel):
    token: str
    server_id: int
    channel_id: int
    content: str
    alternate_id: int = 0
    is_action: bool = False  # For roleplay actions

@app.post("/register")
def register(request: RegisterRequest, db: Session = Depends(get_db)):
    existing_user = db.query(User).filter_by(username=request.username).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Username already exists")
    new_user = User(username=request.username, display_name=request.display_name, password=request.password)
    db.add(new_user)
    db.commit()
    return {"message": "User registered successfully", "user_id": new_user.id}

@app.post("/login")
def login(request: RegisterRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == request.username, User.password == request.password).first()
    if not user:
        raise HTTPException(status_code=400, detail="Invalid credentials")
    update_user_activity(request.username, db)
    new_token = Token(user_id=user.id, token=str(uuid.uuid4()))
    db.add(new_token)
    db.commit()
    return {"message": "Logged in", "token": new_token.token}

@app.post("/get-self")
def get_self(request: dict = Body(...), db: Session = Depends(get_db)):
    token_entry = db.query(Token).filter(Token.token == request['token']).first().user_id
    user = db.query(User).filter(User.id == token_entry).first()
    response = {
        "username": user.username,
        "id": user.id,
        "display_name": user.display_name,
        "profile_picture": user.profile_picture if user.profile_picture else "hidden.png",
    }
    return response

@app.get('/chat')
def chat():
    return FileResponse("hi.html")

@app.get('/hidden.png')
def hidden():
    return FileResponse("hidden.png")

@app.post("/logout")
def logout(request: TokenRequest, db: Session = Depends(get_db)):
    token = db.query(Token).filter(Token.token == request.token).first()
    if not token:
        raise HTTPException(status_code=400, detail="Invalid token")
    user_id = token.user_id
    db.delete(token)
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=400, detail="User not found")
    user.online = False
    db.commit()
    return {"message": "Logged out"}

@app.post("/upload-profile-picture")
def upload_profile_picture(request: dict = Body(...), db: Session = Depends(get_db)):
    token_entry = db.query(Token).filter(Token.token == request.get('token')).first()
    if not token_entry:
        raise HTTPException(status_code=400, detail="Invalid token")
    user = db.query(User).filter(User.id == token_entry.user_id).first()
    image_url = request.get("image_url")
    if not image_url:
        raise HTTPException(status_code=400, detail="Image URL is required")
    if not user:
        raise HTTPException(status_code=400, detail="User not found")
    user.profile_picture = image_url
    db.commit()
    return {"message": "Profile picture updated", "image_url": image_url}

@app.post("/create-server")
def create_server(request: CreateServerRequest, db: Session = Depends(get_db)):
    new_server = Server(name=request.name)
    db.add(new_server)
    db.commit()
    return {"message": "Server created", "server": new_server.id}

@app.post("/create-channel")
def create_channel(request: CreateChannelRequest, db: Session = Depends(get_db)):
    if not db.query(Server).filter(Server.id == request.server_id).first():
        raise HTTPException(status_code=400, detail="Server not found")
    new_channel = Channel(name=request.name, server_id=request.server_id)
    db.add(new_channel)
    db.commit()
    return {"message": "Channel created", "channel": new_channel.id}

# WebSocket endpoint for real-time channel messages
@app.websocket("/ws/{channel_id}")
async def websocket_endpoint(websocket: WebSocket, channel_id: int, db: Session = Depends(get_db)):
    await websocket.accept()
    if channel_id not in active_connections:
        active_connections[channel_id] = []
    active_connections[channel_id].append(websocket)
    try:
        while True:
            data = await websocket.receive_json()
            token = data.get("token")
            content = data.get("content")
            alternate_id = data.get("alternate_id", 0)
            is_action = data.get("is_action", False)
            
            token_entry = db.query(Token).filter(Token.token == token).first()
            if not token_entry:
                await websocket.send_json({"error": "Invalid token"})
                continue
            
            user_id = token_entry.user_id
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                await websocket.send_json({"error": "User not found"})
                continue
            
            new_message = Message(
                user_id=user_id,
                channel_id=channel_id,
                content=content,
                timestamp=datetime.utcnow(),
                is_action=is_action,
                alternate_id=alternate_id
            )
            db.add(new_message)
            db.commit()
            
            response = {
                "event": "new",
                "id": new_message.id,
                "user_id": user.id,
                "username": user.username,
                "display_name": user.display_name if alternate_id == 0 else db.query(AlternateProfile).filter(AlternateProfile.id == alternate_id).first().name,
                "content": content,
                "timestamp": new_message.timestamp.isoformat(),
                "is_action": is_action,
                "is_edited": False,
                "profile_picture": user.profile_picture if alternate_id == 0 else db.query(AlternateProfile).filter(AlternateProfile.id == alternate_id).first().icon,
            }
            for conn in active_connections[channel_id]:
                await conn.send_json(response)
    except WebSocketDisconnect:
        active_connections[channel_id].remove(websocket)

# Endpoint to fetch all messages in a channel (for initial load)
@app.get("/messages")
def get_messages(channel_id: int, db: Session = Depends(get_db)):
    messages = db.query(Message).filter(Message.channel_id == channel_id).all()
    response = []
    for msg in messages:
        user = db.query(User).filter(User.id == msg.user_id).first()
        display_name = user.display_name
        profile_picture = user.profile_picture if user and user.profile_picture else "hidden.png",
        if msg.alternate_id and msg.alternate_id != 0:
            alt = db.query(AlternateProfile).filter(AlternateProfile.id == msg.alternate_id).first()
            if alt:
                display_name = alt.name
                profile_picture = alt.icon if alt.icon else "hidden.png"
        response.append({
            "id": msg.id,
            "user_id": msg.user_id,
            "username": user.username if user else "unknown",
            "display_name": display_name,
            "profile_picture": profile_picture,
            "content": msg.content,
            "timestamp": msg.timestamp.isoformat(),
            "is_action": msg.is_action,
            "is_edited": msg.is_edited
        })
    return {"messages": response}

@app.get("/users")
def get_users(db: Session = Depends(get_db)):
    users = db.query(User).all()
    return [{"id": u.id, "username": u.username, "display_name": u.display_name, "online": u.online, "profile_picture": u.profile_picture, "alternates": u.alternates} for u in users]

@app.get("/servers")
def get_servers(db: Session = Depends(get_db)):
    servers = db.query(Server).all()
    return servers

@app.get("/channels")
def get_channels(server_id: int, db: Session = Depends(get_db)):
    channels = db.query(Channel).filter(Channel.server_id == server_id).all()
    return channels

# Endpoint to update username and display_name (but not user ID)
@app.post("/update-profile")
def update_profile(token: str, username: str = None, display_name: str = None, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == (db.query(Token).filter(Token.token == token).first().user_id)).first()
    if not user:
        raise HTTPException(status_code=400, detail="User not found")
    if username != "":
        user.username = username
    if display_name != "":
        user.display_name = display_name
    db.commit()
    return {"message": "Profile updated"}

class CreateAlternateRequest(BaseModel):
    user_id: int
    name: str
    icon: str = None

@app.post("/create-alternate")
def create_alternate(request: CreateAlternateRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == request.user_id).first()
    if not user:
        raise HTTPException(status_code=400, detail="User not found")
    if len(user.alternates) >= 20:
        raise HTTPException(status_code=400, detail="Maximum of 20 alternates allowed")
    new_alternate = AlternateProfile(
        user_id=request.user_id,
        name=request.name,
        icon=request.icon
    )
    db.add(new_alternate)
    db.commit()
    return {"message": "Alternate created", "alternate_id": new_alternate.id}

@app.delete("/delete-alternate")
def delete_alternate(alternate_id: int, db: Session = Depends(get_db)):
    alternate = db.query(AlternateProfile).filter(AlternateProfile.id == alternate_id).first()
    if not alternate:
        raise HTTPException(status_code=400, detail="Alternate not found")
    alternate.user_id = 0  # Unlink the alternate from the user
    db.commit()
    return {"message": "Alternate deleted"}

# Edit message endpoint with WebSocket broadcast update
@app.put("/edit-message")
def edit_message(request: dict = Body(...), db: Session = Depends(get_db)):
    message_id = request.get("message_id")
    user_id = request.get("user_id")
    new_content = request.get("new_content")
    if not message_id or not user_id or not new_content:
        raise HTTPException(status_code=400, detail="Message ID, User ID, and new content are required")
    message = db.query(Message).filter(Message.id == message_id).first()
    if not message:
        raise HTTPException(status_code=400, detail="Message not found")
    if message.user_id != user_id:
        raise HTTPException(status_code=403, detail="You can only edit your own messages")
    message.content = new_content
    message.is_edited = True
    db.commit()
    # Broadcast edit event
    payload = {
        "event": "edit",
        "id": message.id,
        "new_content": new_content,
        "is_edited": True
    }
    broadcast_to_channel(message.channel_id, payload)
    return {"message": "Message edited", "new_content": new_content}

# Delete message endpoint with WebSocket broadcast removal
@app.delete("/delete-message")
def delete_message(request: dict = Body(...), db: Session = Depends(get_db)):
    message_id = request.get("message_id")
    user_id = request.get("user_id")
    if not message_id or not user_id:
        raise HTTPException(status_code=400, detail="Message ID and User ID are required")
    message = db.query(Message).filter(Message.id == message_id).first()
    if not message:
        raise HTTPException(status_code=400, detail="Message not found")
    if message.user_id != user_id:
        raise HTTPException(status_code=403, detail="You can only delete your own messages")
    channel_id = message.channel_id
    db.delete(message)
    db.commit()
    # Broadcast deletion event
    payload = {
        "event": "delete",
        "id": message_id
    }
    broadcast_to_channel(channel_id, payload)
    return {"message": "Message deleted"}

# ---------------------------
# Private Message Endpoints
# ---------------------------
class PrivateMessageRequest(BaseModel):
    token: str
    receiver_id: int
    content: str

@app.post("/send-private")
def send_private_message(request: PrivateMessageRequest, db: Session = Depends(get_db)):
    token_entry = db.query(Token).filter(Token.token == request.token).first()
    if not token_entry:
        raise HTTPException(status_code=400, detail="Invalid token")
    sender_id = token_entry.user_id
    new_pm = PrivateMessage(
        sender_id=sender_id,
        receiver_id=request.receiver_id,
        content=request.content,
        timestamp=datetime.utcnow()
    )
    db.add(new_pm)
    db.commit()
    return {"message": "Private message sent", "pm_id": new_pm.id}

@app.get("/private-messages")
def get_private_messages(token: str, other_user_id: int, db: Session = Depends(get_db)):
    token_entry = db.query(Token).filter(Token.token == token).first()
    if not token_entry:
        raise HTTPException(status_code=400, detail="Invalid token")
    user_id = token_entry.user_id
    messages = db.query(PrivateMessage).filter(
        or_(
            (PrivateMessage.sender_id == user_id) & (PrivateMessage.receiver_id == other_user_id),
            (PrivateMessage.sender_id == other_user_id) & (PrivateMessage.receiver_id == user_id)
        )
    ).all()
    response = []
    for pm in messages:
        response.append({
            "id": pm.id,
            "sender_id": pm.sender_id,
            "receiver_id": pm.receiver_id,
            "content": pm.content,
            "timestamp": pm.timestamp.isoformat(),
            "is_edited": pm.is_edited
        })
    return {"private_messages": response}

@app.put("/edit-private")
def edit_private_message(request: dict = Body(...), db: Session = Depends(get_db)):
    pm_id = request.get("pm_id")
    user_id = request.get("user_id")
    new_content = request.get("new_content")
    if not pm_id or not user_id or not new_content:
        raise HTTPException(status_code=400, detail="PM ID, User ID, and new content are required")
    pm = db.query(PrivateMessage).filter(PrivateMessage.id == pm_id).first()
    if not pm:
        raise HTTPException(status_code=400, detail="Private message not found")
    if pm.sender_id != user_id:
        raise HTTPException(status_code=403, detail="You can only edit your own private messages")
    pm.content = new_content
    pm.is_edited = True
    db.commit()
    return {"message": "Private message edited", "new_content": new_content}

@app.delete("/delete-private")
def delete_private_message(request: dict = Body(...), db: Session = Depends(get_db)):
    pm_id = request.get("pm_id")
    user_id = request.get("user_id")
    if not pm_id or not user_id:
        raise HTTPException(status_code=400, detail="PM ID and User ID are required")
    pm = db.query(PrivateMessage).filter(PrivateMessage.id == pm_id).first()
    if not pm:
        raise HTTPException(status_code=400, detail="Private message not found")
    if pm.sender_id != user_id:
        raise HTTPException(status_code=403, detail="You can only delete your own private messages")
    db.delete(pm)
    db.commit()
    return {"message": "Private message deleted"}

# ---------------------------
# Run the application
# ---------------------------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
