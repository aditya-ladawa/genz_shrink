// src/app/auth/signup/page.js

'use client'

export default function SignupPage() {
  async function handleSubmit(e) {
    e.preventDefault()
    const formData = new FormData(e.target)
    
    try {
      const response = await fetch('/api/signup', {
        method: 'POST',
        body: JSON.stringify({
          firstName: formData.get('firstName'),
          lastName: formData.get('lastName'),
          age: formData.get('age'),
          email: formData.get('email'),
          password: formData.get('password')
        }),
        headers: {
          'Content-Type': 'application/json'
        }
      })
      
      if (response.ok) {
        window.location.href = '/chat'
      }
    } catch (error) {
      console.error('Signup failed:', error)
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className="block text-gray-700">First Name</label>
          <input 
            type="text" 
            name="firstName"
            className="w-full p-2 border rounded-md"
            required
          />
        </div>
        <div>
          <label className="block text-gray-700">Last Name</label>
          <input 
            type="text" 
            name="lastName"
            className="w-full p-2 border rounded-md"
            required
          />
        </div>
      </div>
      
      <div>
        <label className="block text-gray-700">Age</label>
        <input
          type="number"
          name="age"
          className="w-full p-2 border rounded-md"
          required
        />
      </div>
      
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
        Create Account
      </button>
    </form>
  )
}