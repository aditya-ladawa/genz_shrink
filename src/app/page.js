// src/app/page.js

export default function Home() {
  return (
    <div className="text-center space-y-8">
      <h1 className="text-4xl font-bold">Your AI Friend That Understands</h1>
      <p className="text-xl text-gray-600">Chat, get advice, and share memes with your virtual companion</p>
      <div className="space-x-4">
        <a href="/auth/login" className="bg-blue-600 text-white px-6 py-3 rounded-lg hover:bg-blue-700">
          Get Started
        </a>
      </div>
    </div>
  )
}