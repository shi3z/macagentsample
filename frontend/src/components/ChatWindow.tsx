import { useState, useRef, useEffect, FormEvent } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { ChatMessage, streamChat } from '../api/client'
import { VoiceInput } from './VoiceInput'
import { VoiceOutput } from './VoiceOutput'

// Extract image paths from message and convert to API URLs
function extractImages(content: string): { text: string; images: string[] } {
  const imageSet = new Set<string>()
  // Match patterns like /tmp/generated_abc123.png
  const regex = /\/tmp\/(generated_[a-f0-9]+\.png)/g
  let match
  while ((match = regex.exec(content)) !== null) {
    // Use relative URL so it works through Vite proxy
    imageSet.add(`/api/images/${match[1]}`)
  }
  return { text: content, images: Array.from(imageSet) }
}

export function ChatWindow() {
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [input, setInput] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [isThinking, setIsThinking] = useState(false)
  const [autoSpeak, setAutoSpeak] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  const sendMessage = async (text: string) => {
    if (!text.trim() || isLoading) return

    const userMessage: ChatMessage = { role: 'user', content: text }
    setMessages((prev) => [...prev, userMessage])
    setInput('')
    setIsLoading(true)
    setIsThinking(false)

    try {
      let assistantContent = ''
      setMessages((prev) => [...prev, { role: 'assistant', content: '' }])

      for await (const event of streamChat(text, messages)) {
        if (event.type === 'thinking') {
          setIsThinking(true)
        } else if (event.type === 'content' && event.content) {
          setIsThinking(false)
          assistantContent += event.content
          setMessages((prev) => {
            const newMessages = [...prev]
            newMessages[newMessages.length - 1] = {
              role: 'assistant',
              content: assistantContent,
            }
            return newMessages
          })
        } else if (event.type === 'done') {
          break
        }
      }

      // Auto-speak response if enabled
      if (autoSpeak && assistantContent && 'speechSynthesis' in window) {
        const utterance = new SpeechSynthesisUtterance(assistantContent)
        utterance.lang = 'ja-JP'
        window.speechSynthesis.speak(utterance)
      }
    } catch (error) {
      console.error('Chat error:', error)
      setMessages((prev) => [
        ...prev.slice(0, -1),
        { role: 'assistant', content: 'Error: Failed to get response' },
      ])
    } finally {
      setIsLoading(false)
      setIsThinking(false)
    }
  }

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault()
    sendMessage(input)
  }

  const handleVoiceResult = (transcript: string) => {
    setInput(transcript)
    sendMessage(transcript)
  }

  return (
    <div className="flex flex-col h-screen bg-gray-900 text-white">
      {/* Header */}
      <header className="bg-gray-800 px-6 py-4 flex items-center justify-between">
        <h1 className="text-xl font-bold">Local Agentic AI</h1>
        <div className="flex items-center gap-4">
          <label className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={autoSpeak}
              onChange={(e) => setAutoSpeak(e.target.checked)}
              className="rounded"
            />
            Auto-speak responses
          </label>
        </div>
      </header>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-6 py-4 space-y-4">
        {messages.length === 0 && (
          <div className="text-center text-gray-500 mt-20">
            <p className="text-lg">Welcome to Local Agentic AI</p>
            <p className="text-sm mt-2">
              Ask me anything. I can search the web, read files, execute code, and more.
            </p>
          </div>
        )}
        {messages.map((msg, idx) => (
          <div
            key={idx}
            className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
          >
            <div
              className={`max-w-3xl rounded-lg px-4 py-3 ${
                msg.role === 'user'
                  ? 'bg-blue-600 text-white'
                  : 'bg-gray-700 text-gray-100'
              }`}
            >
              {msg.role === 'assistant' ? (
                (() => {
                  const { text, images } = extractImages(msg.content)
                  return (
                    <>
                      <div className="prose prose-invert prose-sm max-w-none prose-table:border-collapse prose-th:border prose-th:border-gray-500 prose-th:px-2 prose-th:py-1 prose-td:border prose-td:border-gray-500 prose-td:px-2 prose-td:py-1">
                        <ReactMarkdown remarkPlugins={[remarkGfm]}>{text}</ReactMarkdown>
                      </div>
                      {images.length > 0 && (
                        <div className="mt-3 space-y-2">
                          {images.map((imgUrl, imgIdx) => (
                            <img
                              key={imgIdx}
                              src={imgUrl}
                              alt="Generated image"
                              className="max-w-full rounded-lg border border-gray-600"
                              onError={(e) => {
                                (e.target as HTMLImageElement).style.display = 'none'
                              }}
                            />
                          ))}
                        </div>
                      )}
                    </>
                  )
                })()
              ) : (
                <div className="whitespace-pre-wrap break-words">{msg.content}</div>
              )}
              {msg.role === 'assistant' && msg.content && (
                <div className="mt-2 flex justify-end">
                  <VoiceOutput text={msg.content} />
                </div>
              )}
            </div>
          </div>
        ))}
        {isLoading && messages[messages.length - 1]?.role === 'assistant' &&
         !messages[messages.length - 1]?.content && (
          <div className="flex justify-start">
            <div className="bg-gray-700 rounded-lg px-4 py-3">
              {isThinking ? (
                <div className="flex items-center gap-2 text-yellow-400">
                  <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none"/>
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"/>
                  </svg>
                  <span>Thinking...</span>
                </div>
              ) : (
                <div className="flex space-x-2">
                  <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" />
                  <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{animationDelay: '0.1s'}} />
                  <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{animationDelay: '0.2s'}} />
                </div>
              )}
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <div className="bg-gray-800 px-6 py-4">
        <form onSubmit={handleSubmit} className="flex gap-4">
          <VoiceInput onResult={handleVoiceResult} />
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Type your message or click the mic to speak..."
            className="flex-1 bg-gray-700 rounded-lg px-4 py-3 text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500"
            disabled={isLoading}
          />
          <button
            type="submit"
            disabled={isLoading || !input.trim()}
            className="bg-blue-500 hover:bg-blue-600 disabled:bg-gray-600 disabled:cursor-not-allowed px-6 py-3 rounded-lg font-semibold transition-colors"
          >
            Send
          </button>
        </form>
      </div>
    </div>
  )
}
