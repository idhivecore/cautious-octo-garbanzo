from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import sqlite3

app = FastAPI()
from fastapi.middleware.cors import CORSMiddleware

# Allow frontend to communicate with backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins (you can restrict to your frontend URL)
    allow_credentials=True,
    allow_methods=["*"],  # Allows all HTTP methods
    allow_headers=["*"],  # Allows all headers
)

# Database setup
conn = sqlite3.connect("users.db", check_same_thread=False)
cursor = conn.cursor()
cursor.execute("CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, username TEXT UNIQUE, password TEXT)")
conn.commit()

# Create posts table if it doesn't exist
cursor.execute("""
    CREATE TABLE IF NOT EXISTS posts (
        id INTEGER PRIMARY KEY,
        username TEXT,
        content TEXT,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
    )
""")
conn.commit()

# Pydantic Models
class UserCreate(BaseModel):
    username: str
    password: str

class UserLogin(BaseModel):
    username: str
    password: str

# User signup
@app.post("/signup/")
def signup(user: UserCreate):
    try:
        cursor.execute("INSERT INTO users (username, password) VALUES (?, ?)", (user.username, user.password))
        conn.commit()
        return {"message": "User created successfully"}
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=400, detail="Username already exists")

# User login
@app.post("/login/")
def login(user: UserLogin):
    cursor.execute("SELECT password FROM users WHERE username = ?", (user.username,))
    user_data = cursor.fetchone()
    
    if not user_data or user.password != user_data[0]:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    return {"message": "Login successful", "username": user.username}

from datetime import datetime

class PostCreate(BaseModel):
    username: str
    content: str

@app.post("/create_post/")
def create_post(post: PostCreate):
    cursor.execute("INSERT INTO posts (username, content, timestamp) VALUES (?, ?, ?)",
                   (post.username, post.content, datetime.utcnow()))
    conn.commit()
    return {"message": "Post created successfully"}

@app.get("/posts/")
def get_all_posts():
    cursor.execute("SELECT id, username, content, timestamp FROM posts ORDER BY timestamp DESC")
    posts = cursor.fetchall()
    return [{"id": p[0], "username": p[1], "content": p[2], "timestamp": p[3]} for p in posts]

@app.get("/posts/{username}/")
def get_user_posts(username: str):
    cursor.execute("SELECT id, content, timestamp FROM posts WHERE username = ? ORDER BY timestamp DESC", (username,))
    posts = cursor.fetchall()
    return [{"id": p[0], "content": p[1], "timestamp": p[2]} for p in posts]

