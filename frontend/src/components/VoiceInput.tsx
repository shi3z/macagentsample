import { useVoiceInput } from '../hooks/useVoice'

interface VoiceInputProps {
  onResult: (text: string) => void
}

export function VoiceInput({ onResult }: VoiceInputProps) {
  const { transcript, listening, isSupported, toggleListening } =
    useVoiceInput({ onResult })

  if (!isSupported) {
    return (
      <div className="text-yellow-500 text-sm">
        Speech recognition not supported in this browser
      </div>
    )
  }

  return (
    <div className="flex items-center gap-2">
      <button
        onClick={toggleListening}
        className={`p-3 rounded-full transition-all ${
          listening
            ? 'bg-red-500 hover:bg-red-600 animate-pulse'
            : 'bg-blue-500 hover:bg-blue-600'
        }`}
        title={listening ? 'Stop listening' : 'Start listening'}
      >
        <svg
          xmlns="http://www.w3.org/2000/svg"
          className="h-6 w-6 text-white"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z"
          />
        </svg>
      </button>
      {listening && transcript && (
        <div className="flex-1 bg-gray-700 rounded px-3 py-2 text-sm">
          {transcript}
        </div>
      )}
    </div>
  )
}
