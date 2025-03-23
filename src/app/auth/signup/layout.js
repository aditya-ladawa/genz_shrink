// src/app/auth/signup/layout.js

export default function SignupLayout({ children }) {
  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-100">
      <div className="w-full max-w-md p-8 bg-white rounded-lg shadow-md">
        <h1 className="text-2xl font-bold text-center mb-6">Create Your Account</h1>
        {children}
        <p className="text-center text-gray-600 mt-6">
          Already have an account?{' '}
          <a href="/auth/login" className="text-blue-600 hover:underline">Login</a>
        </p>
      </div>
    </div>
  )
}