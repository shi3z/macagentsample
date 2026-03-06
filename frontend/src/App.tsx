import { useEffect, useState } from 'react'
import { ChatWindow } from './components/ChatWindow'
import { checkHealth } from './api/client'

function App() {
  const [status, setStatus] = useState<'loading' | 'connected' | 'error'>('loading')
  const [errorMessage, setErrorMessage] = useState('')

  useEffect(() => {
    const check = async () => {
      try {
        const health = await checkHealth()
        if (health.ollama_connected) {
          setStatus('connected')
        } else {
          setStatus('error')
          setErrorMessage('Ollama is not running. Please start Ollama first.')
        }
      } catch (err) {
        setStatus('error')
        setErrorMessage('Cannot connect to backend. Please start the server.')
      }
    }

    check()
    const interval = setInterval(check, 30000) // Check every 30 seconds
    return () => clearInterval(interval)
  }, [])

  if (status === 'loading') {
    return (
      <div className="flex items-center justify-center h-screen bg-gray-900 text-white">
        <div className="text-center">
          <div className="animate-spin w-12 h-12 border-4 border-blue-500 border-t-transparent rounded-full mx-auto mb-4" />
          <p>Connecting to server...</p>
        </div>
      </div>
    )
  }

  if (status === 'error') {
    return (
      <div className="flex items-center justify-center h-screen bg-gray-900 text-white">
        <div className="text-center max-w-md">
          <div className="text-red-500 text-6xl mb-4">!</div>
          <h1 className="text-2xl font-bold mb-4">Connection Error</h1>
          <p className="text-gray-400 mb-6">{errorMessage}</p>
          <button
            onClick={() => window.location.reload()}
            className="bg-blue-500 hover:bg-blue-600 px-6 py-3 rounded-lg"
          >
            Retry
          </button>
        </div>
      </div>
    )
  }

  return <ChatWindow />
}

export default App
