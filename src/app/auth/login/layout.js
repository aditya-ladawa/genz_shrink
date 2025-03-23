// src/app/auth/login/layout.js
export default function LoginLayout({ children }) {
  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-100">
      <div className="w-full max-w-md p-8 bg-white rounded-lg shadow-md">
        <h1 className="text-2xl font-bold text-center mb-6">Welcome Back!</h1>
        {children}
        <p className="text-center text-gray-600 mt-6">
          Don't have an account?{' '}
          <a href="/auth/signup" className="text-blue-600 hover:underline">Sign up</a>
        </p>
      </div>
    </div>
  )
}