"use client";

import React from "react";
import { useRouter } from "next/router";
import { useEffect, useState } from "react";
import axios from "axios";

export default function UserProfile() {
  const router = useRouter();
  const { id } = router.query;
  const [user, setUser] = useState<any>(null);
  const [posts, setPosts] = useState<any[]>([]);

  useEffect(() => {
    if (id) {
      // Fetch user posts; you might add an endpoint to fetch user info separately if needed
      axios.get(`https://cautious-octo-garbanzo.onrender.com/posts/user/${id}/`)
        .then(response => {
          setPosts(response.data);
          if (response.data.length > 0) {
            setUser(response.data[0].user);
          }
        })
        .catch(error => console.error("Error fetching user posts:", error));
    }
  }, [id]);

  if (!user) return <div>Loading...</div>;

  return (
    <div className="min-h-screen bg-gray-900 text-gray-100 p-6">
      <div className="max-w-2xl mx-auto bg-gray-800 p-4 rounded-lg shadow mb-6">
        <div className="flex items-center space-x-4">
          {user.profile_icon && (
            <img src={user.profile_icon} alt="Profile Icon" className="w-12 h-12 rounded-full" />
          )}
          <div>
            <p className="font-bold">{user.display_name || user.username}</p>
            <p className="text-sm text-gray-400">@{user.username}</p>
          </div>
        </div>
        <p className="mt-2">{user.bio}</p>
      </div>
      <div className="max-w-2xl mx-auto space-y-4">
        {posts.length === 0 ? (
          <p className="text-center text-gray-500">No posts yet.</p>
        ) : (
          posts.map((post) => (
            <div key={post.id} className="bg-gray-800 p-4 rounded-lg shadow">
              <p>{post.content}</p>
              <p className="text-sm text-gray-500">{post.timestamp}</p>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
