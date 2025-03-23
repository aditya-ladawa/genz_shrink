// src/app/auth/login/page.js

'use client'

export default function LoginPage() {
  async function handleSubmit(e) {
    e.preventDefault()
    const formData = new FormData(e.target)
    
    try {
      const response = await fetch('/api/login', {
        method: 'POST',
        body: JSON.stringify({
          email: formData.get('email'),
          password: formData.get('password')
        }),
        headers: {
          'Content-Type': 'application/json'
        },
        credentials: 'include',
      })
      
      if (response.ok) {
        window.location.href = '/chat/new'
      }
    } catch (error) {
      console.error('Login failed:', error)
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      <div>
        <label className="block text-gray-700">Email</label>
        <input 
          type="email" 
          name="email"
          className="w-full p-2 border rounded-md"
          required
        />
      </div>
      
      <div>
        <label className="block text-gray-700">Password</label>
        <input
          type="password"
          name="password"
          className="w-full p-2 border rounded-md"
          required
        />
      </div>
      
      <button 
        type="submit"
        className="w-full bg-blue-600 text-white py-2 rounded-md hover:bg-blue-700"
      >
        Login
      </button>
    </form>
  )
}