// src/app/layout.js
export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <body className="min-h-screen flex flex-col">
        <header className="bg-blue-600 text-white p-4">
          <nav className="container mx-auto flex justify-between items-center">
            <h1 className="text-xl font-bold">MemeFriend</h1>
            <div className="space-x-4">
              <a href="/auth/login" className="hover:text-blue-200">Login</a>
              <a href="/auth/signup" className="hover:text-blue-200">Sign Up</a>
            </div>
          </nav>
        </header>
        
        <main className="flex-grow container mx-auto p-4">{children}</main>
        
        <footer className="bg-gray-800 text-white p-4 mt-auto">
          <div className="container mx-auto text-center">
            <p>© 2024 MemeFriend. All rights reserved.</p>
          </div>
        </footer>
      </body>
    </html>
  )
}