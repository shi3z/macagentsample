export interface ChatMessage {
  role: 'user' | 'assistant'
  content: string
}

export interface ChatRequest {
  message: string
  history?: ChatMessage[]
  stream?: boolean
}

const API_BASE = '/api'

export interface StreamEvent {
  type: 'thinking' | 'content' | 'done'
  content?: string
}

export async function* streamChat(
  message: string,
  history: ChatMessage[] = []
): AsyncGenerator<StreamEvent, void, unknown> {
  const response = await fetch(`${API_BASE}/chat`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      message,
      history,
      stream: true,
    }),
  })

  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`)
  }

  const reader = response.body?.getReader()
  if (!reader) {
    throw new Error('No response body')
  }

  const decoder = new TextDecoder()
  let buffer = ''
  let currentEvent = 'message'

  while (true) {
    const { done, value } = await reader.read()
    if (done) break

    buffer += decoder.decode(value, { stream: true })
    const lines = buffer.split('\n')
    buffer = lines.pop() || ''

    for (const line of lines) {
      if (line.startsWith('event: ')) {
        currentEvent = line.slice(7).trim()
      } else if (line.startsWith('data: ')) {
        try {
          const data = JSON.parse(line.slice(6))
          if (currentEvent === 'thinking') {
            yield { type: 'thinking' }
          } else if (data.content) {
            yield { type: 'content', content: data.content }
          }
          if (data.done) {
            yield { type: 'done' }
            return
          }
        } catch {
          // Ignore parse errors
        }
      }
    }
  }
}

export async function checkHealth(): Promise<{
  status: string
  ollama_connected: boolean
}> {
  const response = await fetch(`${API_BASE}/health`)
  return response.json()
}

export async function uploadDocument(file: File): Promise<{
  status: string
  document_id: string
  filename: string
}> {
  const formData = new FormData()
  formData.append('file', file)

  const response = await fetch(`${API_BASE}/documents/upload`, {
    method: 'POST',
    body: formData,
  })

  if (!response.ok) {
    throw new Error(`Upload failed: ${response.status}`)
  }

  return response.json()
}
