// src/app/chat/[conversationId]/layout.js

export default function ConversationLayout({ children }) {
  return (
    <div className="min-h-screen flex flex-col">
      <header className="bg-blue-600 text-white p-4">
        <nav className="container mx-auto flex justify-between items-center">
          <h1 className="text-xl font-bold">Chat Conversation</h1>
          <div className="space-x-4">
            <a href="/chat/new" className="hover:text-blue-200">New Chat</a>
            <a href="/chat" className="hover:text-blue-200">All Chats</a>
            <a href="/" className="hover:text-blue-200">Home</a>
            <form action="/api/logout" method="POST">
              <button type="submit" className="hover:text-blue-200">
                Logout
              </button>
            </form>
          </div>
        </nav>
      </header>

      <main className="flex-grow container mx-auto p-4">
        <div className="max-w-4xl mx-auto">
          {children}
        </div>
      </main>

      <footer className="bg-gray-800 text-white p-4 mt-auto">
        <div className="container mx-auto text-center">
          <p>© 2024 MemeFriend. Continue your conversation!</p>
        </div>
      </footer>
    </div>
  )
}