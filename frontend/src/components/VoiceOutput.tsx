import { useVoiceOutput } from '../hooks/useVoice'

interface VoiceOutputProps {
  text: string
}

export function VoiceOutput({ text }: VoiceOutputProps) {
  const { speak, stop, isSpeaking, isSupported } = useVoiceOutput()

  if (!isSupported) {
    return null
  }

  return (
    <button
      onClick={() => (isSpeaking ? stop() : speak(text))}
      className={`p-2 rounded transition-all ${
        isSpeaking
          ? 'bg-orange-500 hover:bg-orange-600'
          : 'bg-gray-600 hover:bg-gray-500'
      }`}
      title={isSpeaking ? 'Stop speaking' : 'Read aloud'}
    >
      <svg
        xmlns="http://www.w3.org/2000/svg"
        className="h-5 w-5 text-white"
        fill="none"
        viewBox="0 0 24 24"
        stroke="currentColor"
      >
        {isSpeaking ? (
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z M9 10h6v4H9z"
          />
        ) : (
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M15.536 8.464a5 5 0 010 7.072m2.828-9.9a9 9 0 010 12.728M5.586 15H4a1 1 0 01-1-1v-4a1 1 0 011-1h1.586l4.707-4.707C10.923 3.663 12 4.109 12 5v14c0 .891-1.077 1.337-1.707.707L5.586 15z"
          />
        )}
      </svg>
    </button>
  )
}
