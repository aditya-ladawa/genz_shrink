'use client';
import { useEffect, useState, useRef } from 'react';
import { use } from 'react';
import { useRouter } from 'next/navigation';

export default function ChatPage({ params }) {
  const router = useRouter();
  const unwrappedParams = use(params);
  const { conversationId: initialConvId } = unwrappedParams;
  const [currentConvId, setCurrentConvId] = useState(initialConvId);
  const [messages, setMessages] = useState([]);
  const [inputValue, setInputValue] = useState('');
  const [isConnected, setIsConnected] = useState(false);
  const [isRecording, setIsRecording] = useState(false);
  const ws = useRef(null);

  useEffect(() => {
    const savedMessages = localStorage.getItem(`chatMessages_${currentConvId}`);
    if (savedMessages) {
      setMessages(JSON.parse(savedMessages));
    }
    fetchMessages();
  }, [currentConvId]);

  useEffect(() => {
    localStorage.setItem(`chatMessages_${currentConvId}`, JSON.stringify(messages));
  }, [messages]);

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
          console.log("Received message:", message); // Debugging

          if (message.type === "new_conversation") {
            window.history.replaceState(null, '', `/chat/${message.conversation_id}`);
            setCurrentConvId(message.conversation_id);
          }

          if (message.type === "ai_message") {
            setMessages(prev => [...prev, {
              type: "AIMessage",
              content: message.content
            }]);
          } else if (message.type === "audio_transcription") {
            setMessages(prev => [...prev, {
              type: "AudioTranscription",
              content: message.content
            }]);
          } else if (message.type === "tool_message") { // Changed from "meme_urls" to "tool_message"
            console.log("Received MemeMessage:", message); // Debugging
            setMessages(prev => [...prev, {
              type: "MemeMessage",
              urls: message.urls  // Array of meme URLs
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
        setTimeout(connectWebSocket, 5000);
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
      ws.current.send(JSON.stringify({ type: "text", content: inputValue }));
      setInputValue('');
    }
  };

  const startRecording = () => {
    if (ws.current?.readyState === WebSocket.OPEN) {
      ws.current.send(JSON.stringify({ type: "audio" }));
      setIsRecording(true);
    }
  };

  const stopRecording = () => {
    if (ws.current?.readyState === WebSocket.OPEN) {
      ws.current.send(JSON.stringify({ type: "stop_audio" }));
      setIsRecording(false);
    }
  };

  if (!isConnected) return <div>Connecting...</div>;

  return (
    <div>
      <h1>Chat: {currentConvId === 'new' ? 'New Chat' : currentConvId}</h1>
      <div>
        {messages.map((msg, i) => (
          <div key={i}>
            {msg.type === "AudioTranscription" ? (
              <div><strong>You:</strong> {msg.content}</div>
            ) : msg.type === "MemeMessage" ? (
              <div>
                {msg.urls.map((url, index) => (
                  <img
                    key={index}
                    src={url}
                    alt={`Meme ${index + 1}`}
                    style={{ width: '500px', height: 'auto', margin: '5px' }} // Inline styles for simplicity
                    onError={(e) => {
                      e.target.onerror = null;
                      e.target.src = '/fallback-meme.png'; // Fallback image if URL is invalid
                    }}
                  />
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
      <button onClick={isRecording ? stopRecording : startRecording}>
        {isRecording ? "Stop Recording" : "Start Recording"}
      </button>
    </div>
  );
}