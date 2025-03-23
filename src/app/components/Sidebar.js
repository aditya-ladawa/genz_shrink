'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'

export default function Sidebar() {
  const [conversations, setConversations] = useState([])

  useEffect(() => {
    async function fetchConversations() {
      try {
        const response = await fetch('http://localhost:8000/fetch_conversations', {
          credentials: 'include'
        })
        
        if (!response.ok) {
          const error = await response.text()
          throw new Error(`HTTP error! status: ${response.status} - ${error}`)
        }
    
        const contentType = response.headers.get('content-type')
        if (!contentType || !contentType.includes('application/json')) {
          throw new TypeError("Response wasn't JSON")
        }
    
        const data = await response.json()
        setConversations(data.conversations || [])
        
      } catch (error) {
        console.error('Fetch error:', error)
        setConversations([]) // Reset to empty array on error
      }
    }

    fetchConversations()
  }, [])

  return (
    <div className="w-64 bg-gray-100 p-4 border-r border-gray-200">
      <h2 className="text-lg font-semibold mb-4">Your Conversations</h2>
      <ul className="space-y-2">
        {conversations.length > 0 ? (
          conversations.map((convo) => (
            <li key={convo.id}>  {/* Changed to convo.id */}
              <Link
                href={`/chat/${convo.id}`} 
                className="block p-2 hover:bg-gray-200 rounded-lg"
              >
                <p className="font-medium">{convo.topic}</p>  {/* Changed to convo.topic */}
                <p className="text-sm text-gray-500">
                  {convo.created_at}  {/* Changed to convo.created_at */}
                </p>
              </Link>
            </li>
          ))
        ) : (
          <p className="text-gray-500">No conversations yet.</p>
        )}
      </ul>
    </div>
  )
}