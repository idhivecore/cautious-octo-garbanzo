from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from pydantic import BaseModel, Field
import sqlite3
from datetime import datetime
import os
from fastapi.middleware.cors import CORSMiddleware
import shutil

app = FastAPI()

# Allow frontend to communicate with backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Ensure uploads folder exists
UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Database setup (users.db)
conn = sqlite3.connect("users.db", check_same_thread=False)
cursor = conn.cursor()

# Create users table with additional fields and length limits enforced by our API layer
cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY,
        username TEXT UNIQUE,
        password TEXT,
        display_name TEXT,
        bio TEXT,
        profile_icon TEXT
    )
""")
conn.commit()

# Create posts table referencing user id
cursor.execute("""
    CREATE TABLE IF NOT EXISTS posts (
        id INTEGER PRIMARY KEY,
        user_id INTEGER,
        content TEXT,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(user_id) REFERENCES users(id)
    )
""")
conn.commit()

# Pydantic models with length limits
class UserCreate(BaseModel):
    username: str = Field(..., max_length=20)
    password: str = Field(..., max_length=50)
    display_name: str = Field("", max_length=50)
    bio: str = Field("", max_length=160)
    profile_icon: str = Field("", max_length=200)

class UserLogin(BaseModel):
    username: str
    password: str

class UserUpdate(BaseModel):
    id: int
    username: str = Field(..., max_length=20)
    display_name: str = Field(..., max_length=50)
    bio: str = Field(..., max_length=160)
    profile_icon: str = Field(..., max_length=200)

class PostCreate(BaseModel):
    user_id: int
    content: str

# User signup
@app.post("/signup/")
def signup(user: UserCreate):
    try:
        cursor.execute(
            "INSERT INTO users (username, password, display_name, bio, profile_icon) VALUES (?, ?, ?, ?, ?)",
            (user.username, user.password, user.display_name, user.bio, user.profile_icon)
        )
        conn.commit()
        return {"message": "User created successfully"}
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=400, detail="Username already exists")

# User login – returns full user info including unchanging id
@app.post("/login/")
def login(user: UserLogin):
    cursor.execute("SELECT id, password, username, display_name, bio, profile_icon FROM users WHERE username = ?", (user.username,))
    user_data = cursor.fetchone()
    if not user_data or user.password != user_data[1]:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return {"message": "Login successful", "user": {
        "id": user_data[0],
        "username": user_data[2],
        "display_name": user_data[3],
        "bio": user_data[4],
        "profile_icon": user_data[5]
    }}

# Profile update endpoint
@app.post("/update_profile/")
def update_profile(user: UserUpdate):
    cursor.execute(
        "UPDATE users SET username = ?, display_name = ?, bio = ?, profile_icon = ? WHERE id = ?",
        (user.username, user.display_name, user.bio, user.profile_icon, user.id)
    )
    conn.commit()
    return {"message": "Profile updated successfully"}

# Endpoint to handle image file upload for profile icons
@app.post("/upload_profile_icon/")
async def upload_profile_icon(file: UploadFile = File(...)):
    file_location = os.path.join(UPLOAD_FOLDER, file.filename)
    with open(file_location, "wb") as f:
        shutil.copyfileobj(file.file, f)
    # In production, you'd generate a full URL here.
    return {"url": f"/{file_location}"}

# Create a new post (only if user exists)
@app.post("/create_post/")
def create_post(post: PostCreate):
    cursor.execute("SELECT id FROM users WHERE id = ?", (post.user_id,))
    if not cursor.fetchone():
        raise HTTPException(status_code=400, detail="User does not exist")
    cursor.execute("INSERT INTO posts (user_id, content, timestamp) VALUES (?, ?, ?)",
                   (post.user_id, post.content, datetime.utcnow()))
    conn.commit()
    return {"message": "Post created successfully"}

# Fetch all posts joined with user info
@app.get("/posts/")
def get_all_posts():
    cursor.execute("""
        SELECT posts.id, posts.content, posts.timestamp, users.id, users.username, users.display_name, users.profile_icon
        FROM posts
        JOIN users ON posts.user_id = users.id
        ORDER BY posts.timestamp DESC
    """)
    rows = cursor.fetchall()
    posts = []
    for r in rows:
        posts.append({
            "id": r[0],
            "content": r[1],
            "timestamp": r[2],
            "user": {
                "id": r[3],
                "username": r[4],
                "display_name": r[5],
                "profile_icon": r[6]
            }
        })
    return posts

# Fetch a single post by ID
@app.get("/post/{post_id}/")
def get_post(post_id: int):
    cursor.execute("""
        SELECT posts.id, posts.content, posts.timestamp, users.id, users.username, users.display_name, users.profile_icon
        FROM posts
        JOIN users ON posts.user_id = users.id
        WHERE posts.id = ?
    """, (post_id,))
    row = cursor.fetchone()
    if row:
        return {
            "id": row[0],
            "content": row[1],
            "timestamp": row[2],
            "user": {
                "id": row[3],
                "username": row[4],
                "display_name": row[5],
                "profile_icon": row[6]
            }
        }
    else:
        raise HTTPException(status_code=404, detail="Post not found")

# Fetch posts for a specific user (by user id)
@app.get("/posts/user/{user_id}/")
def get_user_posts(user_id: int):
    cursor.execute("""
        SELECT posts.id, posts.content, posts.timestamp, users.id, users.username, users.display_name, users.profile_icon
        FROM posts
        JOIN users ON posts.user_id = users.id
        WHERE users.id = ?
        ORDER BY posts.timestamp DESC
    """, (user_id,))
    rows = cursor.fetchall()
    posts = []
    for r in rows:
        posts.append({
            "id": r[0],
            "content": r[1],
            "timestamp": r[2],
            "user": {
                "id": r[3],
                "username": r[4],
                "display_name": r[5],
                "profile_icon": r[6]
            }
        })
    return posts
