'use client';
import { useEffect, useState, useRef } from 'react';
import { use } from 'react'; // Import the `use` function
import { useRouter } from 'next/navigation';

export default function ChatPage({ params }) {
  const router = useRouter();
  const unwrappedParams = use(params); // Unwrap the params Promise
  const { conversationId: initialConvId } = unwrappedParams; // Access the property after unwrapping
  const [currentConvId, setCurrentConvId] = useState(initialConvId);
  const [messages, setMessages] = useState([]);
  const [inputValue, setInputValue] = useState('');
  const [isConnected, setIsConnected] = useState(false);
  const ws = useRef(null);

  // Fetch messages from the server on page load
  useEffect(() => {
    const savedMessages = localStorage.getItem(`chatMessages_${currentConvId}`);
    if (savedMessages) {
      setMessages(JSON.parse(savedMessages));
    }
    fetchMessages();
  }, [currentConvId]);

  // Save messages to localStorage whenever they change
  useEffect(() => {
    localStorage.setItem(`chatMessages_${currentConvId}`, JSON.stringify(messages));
  }, [messages]);

  // WebSocket connection logic
  useEffect(() => {
    const connectWebSocket = () => {
      ws.current = new WebSocket(`ws://localhost:8000/llm_chat/${initialConvId}`);

      ws.current.onopen = () => {
        setIsConnected(true);
        if (initialConvId !== 'new') fetchMessages();
      };

      ws.current.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data);

          if (message.type === "new_conversation") {
            window.history.replaceState(null, '', `/chat/${message.conversation_id}`);
            setCurrentConvId(message.conversation_id);
          }

          if (message.type === "ai_message") {
            setMessages(prev => [...prev, {
              type: "AIMessage",
              content: message.content
            }]);
          } else if (message.type === "tool_message") {  // Handle ToolMessage
            const urls = message.content.split(/(https?:\/\/[^\s]+)/g).filter(Boolean);  // Parse URLs
            setMessages(prev => [...prev, {
              type: "ToolMessage",
              content: message.content,  // Include ToolMessage content
              urls: urls  // Include parsed meme URLs
            }]);
          } else if (message.type === "error") {
            setMessages(prev => [...prev, {
              type: "Error",
              content: message.message
            }]);
          }
        } catch (error) {
          console.error("Error parsing WebSocket message:", error);
        }
      };

      ws.current.onclose = () => {
        setIsConnected(false);
        console.log("WebSocket disconnected. Reconnecting...");
        setTimeout(connectWebSocket, 5000); // Reconnect after 5 seconds
      };

      ws.current.onerror = (error) => {
        console.error("WebSocket error:", error);
      };
    };

    connectWebSocket();

    return () => {
      if (ws.current) {
        ws.current.close();
      }
    };
  }, [initialConvId]);

  const fetchMessages = async () => {
    try {
      const res = await fetch(`http://localhost:8000/chat/${currentConvId}`, { credentials: 'include' });

      if (!res.ok) throw new Error('Failed to fetch messages');
      const data = await res.json();
      setMessages(data.messages || []);
    } catch (error) {
      console.error('Error fetching messages:', error);
      setMessages([]);
    }
  };

  const sendMessage = () => {
    if (inputValue.trim() && ws.current?.readyState === WebSocket.OPEN) {
      ws.current.send(inputValue);
      setInputValue('');
    }
  };

  if (!isConnected) return <div>Connecting...</div>;

  return (
    <div>
      <h1>Chat: {currentConvId === 'new' ? 'New Chat' : currentConvId}</h1>
      <div className="chat-messages">
        {messages.map((msg, i) => (
          <div key={i} className={`message ${msg.type}`}>
            {msg.type === "ToolMessage" ? (  // Render ToolMessage
              <div>
                <div><strong>ToolMessage:</strong> {msg.content}</div>
                <div className="meme-grid">
                  {(msg.urls || []).filter(url => url.startsWith('http')).map((url, index) => (  // Filter valid URLs
                    <img key={index} src={url} alt={`Meme ${index + 1}`} className="meme-item" onError={(e) => { e.target.onerror = null; e.target.src = '/fallback-meme.png'; }} />
                  ))}
                </div>
              </div>
            ) : msg.type === "MemeMessage" ? (  // Render MemeMessage (if still used)
              <div className="meme-grid">
                {(msg.urls || []).filter(url => url.startsWith('http')).map((url, index) => (  // Filter valid URLs
                  <img key={index} src={url} alt={`Meme ${index + 1}`} className="meme-item" onError={(e) => { e.target.onerror = null; e.target.src = '/fallback-meme.png'; }} />
                ))}
              </div>
            ) : (
              <div><strong>{msg.type}:</strong> {msg.content}</div>
            )}
          </div>
        ))}
      </div>
      <input value={inputValue} onChange={(e) => setInputValue(e.target.value)} placeholder="Type a message..." onKeyPress={(e) => e.key === 'Enter' && sendMessage()} />
      <button onClick={sendMessage}>Send</button>
    </div>
  );
}