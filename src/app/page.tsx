"use client";

import { useEffect, useState } from "react";
import axios from "axios";

export default function Home() {
  const [posts, setPosts] = useState([]);
  const [username, setUsername] = useState("");
  const [content, setContent] = useState("");

  useEffect(() => {
    fetchPosts();
  }, []);

  const fetchPosts = async () => {
    try {
      const response = await axios.get("https://cautious-octo-garbanzo.onrender.com/posts/");
      console.log("API Response:", response.data); // Debugging step
      setPosts(Array.isArray(response.data) ? response.data : []); // Ensure posts is always an array
    } catch (error) {
      console.error("Error fetching posts:", error);
      setPosts([]); // Set empty array on error
    }
  };
  

  const createPost = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!username || !content) return alert("Please enter both fields");

    try {
      await axios.post("https://cautious-octo-garbanzo.onrender.com/create_post/", { username, content });
      setUsername("");
      setContent("");
      fetchPosts();
    } catch (error) {
      console.error("Error creating post:", error);
    }
  };

  return (
    <div className="min-h-screen bg-gray-100 p-6">
      <h1 className="text-3xl font-bold text-center mb-6">Microblog</h1>

      {/* Create Post Form */}
      <div className="max-w-md mx-auto bg-white p-4 rounded-lg shadow mb-6">
        <input
          type="text"
          placeholder="Your username"
          value={username}
          onChange={(e) => setUsername(e.target.value)}
          className="w-full p-2 border rounded mb-2"
        />
        <textarea
          placeholder="What's on your mind?"
          value={content}
          onChange={(e) => setContent(e.target.value)}
          className="w-full p-2 border rounded mb-2"
        />
        <button
          onClick={createPost}
          className="w-full bg-blue-500 text-white p-2 rounded"
        >
          Post
        </button>
      </div>

      {/* Display Posts */}
      <div className="max-w-2xl mx-auto space-y-4">
        {posts.length === 0 ? (
          <p className="text-center text-gray-500">No posts yet.</p>
        ) : (
          posts.map((post) => (
            <div key={post.id} className="bg-white p-4 rounded-lg shadow">
              <p className="font-semibold">@{post.username}</p>
              <p className="text-gray-700">{post.content}</p>
              <p className="text-sm text-gray-400">{post.timestamp}</p>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
