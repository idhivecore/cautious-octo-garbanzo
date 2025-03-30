"use client";

import React from "react";
import { useRouter } from "next/router";
import { useEffect, useState } from "react";
import axios from "axios";

export default function PostDetail() {
  const router = useRouter();
  const { id } = router.query;
  const [post, setPost] = useState<any>(null);

  useEffect(() => {
    if (id) {
      axios.get(`https://cautious-octo-garbanzo.onrender.com/post/${id}/`)
        .then(response => setPost(response.data))
        .catch(error => console.error("Error fetching post:", error));
    }
  }, [id]);

  if (!post) return <div>Loading...</div>;

  return (
    <div className="min-h-screen bg-gray-900 text-gray-100 p-6">
      <div className="max-w-2xl mx-auto bg-gray-800 p-4 rounded-lg shadow">
        <div className="flex items-center space-x-4">
          {post.user.profile_icon && (
            <img src={post.user.profile_icon} alt="Profile Icon" className="w-10 h-10 rounded-full" />
          )}
          <div>
            <p className="font-bold">{post.user.display_name || post.user.username}</p>
            <p className="text-sm text-gray-400">@{post.user.username}</p>
          </div>
        </div>
        <p className="mt-2">{post.content}</p>
        <p className="text-sm text-gray-500">{post.timestamp}</p>
      </div>
    </div>
  );
}
