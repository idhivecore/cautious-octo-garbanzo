"use client";

import React from "react";
import { useEffect, useState } from "react";
import axios from "axios";

interface User {
  id: number;
  username: string;
  display_name: string;
  bio: string;
  profile_icon: string;
}

interface Post {
  id: string;
  content: string;
  timestamp: string;
  user: User;
}

export default function Home() {
  const [posts, setPosts] = useState<Post[]>([]);
  const [loggedInUser, setLoggedInUser] = useState<User | null>(null);
  
  // Login state
  const [loginUsername, setLoginUsername] = useState("");
  const [loginPassword, setLoginPassword] = useState("");
  
  // Signup state
  const [signupUsername, setSignupUsername] = useState("");
  const [signupPassword, setSignupPassword] = useState("");
  const [signupDisplayName, setSignupDisplayName] = useState("");
  const [signupBio, setSignupBio] = useState("");
  const [signupProfileIcon, setSignupProfileIcon] = useState("");
  
  // Post state
  const [postContent, setPostContent] = useState("");

  useEffect(() => {
    fetchPosts();
    const interval = setInterval(fetchPosts, 5000); // refresh every 10 seconds
    return () => clearInterval(interval);
  }, []);
  

  const fetchPosts = async () => {
    try {
      const response = await axios.get("https://cautious-octo-garbanzo.onrender.com/posts/");
      setPosts(Array.isArray(response.data) ? response.data : []);
    } catch (error) {
      console.error("Error fetching posts:", error);
      setPosts([]);
    }
  };

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const response = await axios.post("https://cautious-octo-garbanzo.onrender.com/login/", {
        username: loginUsername,
        password: loginPassword,
      });
      setLoggedInUser(response.data.user);
      setLoginUsername("");
      setLoginPassword("");
    } catch (error) {
      console.error("Login error:", error);
      alert("Login failed");
    }
  };

  const handleSignup = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await axios.post("https://cautious-octo-garbanzo.onrender.com/signup/", {
        username: signupUsername,
        password: signupPassword,
        display_name: signupDisplayName,
        bio: signupBio,
        profile_icon: signupProfileIcon,
      });
      alert("Signup successful! Please log in.");
      setSignupUsername("");
      setSignupPassword("");
      setSignupDisplayName("");
      setSignupBio("");
      setSignupProfileIcon("");
    } catch (error) {
      console.error("Signup error:", error);
      alert("Signup failed");
    }
  };

  const handleCreatePost = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!loggedInUser) return alert("You must be logged in to post.");
    try {
      await axios.post("https://cautious-octo-garbanzo.onrender.com/create_post/", {
        user_id: loggedInUser.id,
        content: postContent,
      });
      setPostContent("");
      fetchPosts();
    } catch (error) {
      console.error("Error creating post:", error);
      alert("Failed to create post");
    }
  };

  const handleLogout = () => {
    setLoggedInUser(null);
  };

  return (
    <div className="min-h-screen bg-gray-900 text-gray-100 p-6">
      <h1 className="text-3xl font-bold text-center mb-6">Microblog (Dark Mode)</h1>
      
      {/* If not logged in, show Login and Signup forms */}
      {!loggedInUser ? (
        <div className="max-w-md mx-auto space-y-6">
          {/* Login Form */}
          <form onSubmit={handleLogin} className="bg-gray-800 p-4 rounded-lg shadow">
            <h2 className="text-xl font-semibold mb-4">Login</h2>
            <input
              type="text"
              placeholder="Username"
              value={loginUsername}
              onChange={(e) => setLoginUsername(e.target.value)}
              className="w-full p-2 mb-2 bg-gray-700 text-gray-100 border rounded"
            />
            <input
              type="password"
              placeholder="Password"
              value={loginPassword}
              onChange={(e) => setLoginPassword(e.target.value)}
              className="w-full p-2 mb-2 bg-gray-700 text-gray-100 border rounded"
            />
            <button type="submit" className="w-full bg-blue-600 hover:bg-blue-700 text-white p-2 rounded">
              Login
            </button>
          </form>

          {/* Signup Form */}
          <form onSubmit={handleSignup} className="bg-gray-800 p-4 rounded-lg shadow">
            <h2 className="text-xl font-semibold mb-4">Sign Up</h2>
            <input
              type="text"
              placeholder="Username"
              value={signupUsername}
              onChange={(e) => setSignupUsername(e.target.value)}
              className="w-full p-2 mb-2 bg-gray-700 text-gray-100 border rounded"
            />
            <input
              type="password"
              placeholder="Password"
              value={signupPassword}
              onChange={(e) => setSignupPassword(e.target.value)}
              className="w-full p-2 mb-2 bg-gray-700 text-gray-100 border rounded"
            />
            <input
              type="text"
              placeholder="Display Name"
              value={signupDisplayName}
              onChange={(e) => setSignupDisplayName(e.target.value)}
              className="w-full p-2 mb-2 bg-gray-700 text-gray-100 border rounded"
            />
            <input
              type="text"
              placeholder="Bio"
              value={signupBio}
              onChange={(e) => setSignupBio(e.target.value)}
              className="w-full p-2 mb-2 bg-gray-700 text-gray-100 border rounded"
            />
            <input
              type="text"
              placeholder="Profile Icon URL"
              value={signupProfileIcon}
              onChange={(e) => setSignupProfileIcon(e.target.value)}
              className="w-full p-2 mb-2 bg-gray-700 text-gray-100 border rounded"
            />
            <button type="submit" className="w-full bg-green-600 hover:bg-green-700 text-white p-2 rounded">
              Sign Up
            </button>
          </form>
        </div>
      ) : (
        <div className="max-w-md mx-auto space-y-4">
          {/* Logged in user header with logout */}
          <div className="flex justify-between items-center bg-gray-800 p-4 rounded-lg shadow">
            <div className="flex items-center space-x-4">
              {loggedInUser.profile_icon && (
                <img src={loggedInUser.profile_icon} alt="Profile Icon" className="w-12 h-12 rounded-full" />
              )}
              <div>
                <p className="font-bold">{loggedInUser.display_name || loggedInUser.username}</p>
                <p className="text-sm text-gray-400">@{loggedInUser.username}</p>
              </div>
            </div>
            <button onClick={handleLogout} className="bg-red-600 hover:bg-red-700 text-white p-2 rounded">
              Logout
            </button>
          </div>

          {/* Post creation form (only for logged in users) */}
          <form onSubmit={handleCreatePost} className="bg-gray-800 p-4 rounded-lg shadow">
            <textarea
              placeholder="What's on your mind?"
              value={postContent}
              onChange={(e) => setPostContent(e.target.value)}
              className="w-full p-2 mb-2 bg-gray-700 text-gray-100 border rounded"
            />
            <button type="submit" className="w-full bg-blue-600 hover:bg-blue-700 text-white p-2 rounded">
              Post
            </button>
          </form>
        </div>
      )}

      {/* Display Posts */}
      <div className="max-w-2xl mx-auto space-y-4 mt-6">
        {posts.length === 0 ? (
          <p className="text-center text-gray-500">No posts yet.</p>
        ) : (
          posts.map((post) => (
            <div key={post.id} className="bg-gray-800 p-4 rounded-lg shadow">
              <div className="flex items-center space-x-4">
                {post.user?.profile_icon && (
                  <img src={post.user.profile_icon} alt="Profile Icon" className="w-10 h-10 rounded-full" />
                )}
                <div>
                  <p className="font-bold">{post.user?.display_name || post.user?.username || "Unknown User"}</p>
                  <p className="text-sm text-gray-400">@{post.user?.username || "unknown"}</p>
                </div>
              </div>
              <p className="mt-2">{post.content}</p>
              <p className="text-sm text-gray-500">{post.timestamp}</p>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
