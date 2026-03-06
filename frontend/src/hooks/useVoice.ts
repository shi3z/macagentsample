import { useCallback, useState, useEffect } from 'react'
import SpeechRecognition, { useSpeechRecognition } from 'react-speech-recognition'

interface UseVoiceOptions {
  onResult?: (transcript: string) => void
  language?: string
}

export function useVoiceInput(options: UseVoiceOptions = {}) {
  const { onResult, language = 'ja-JP' } = options
  const [isSupported, setIsSupported] = useState(true)

  const {
    transcript,
    listening,
    resetTranscript,
    browserSupportsSpeechRecognition,
  } = useSpeechRecognition()

  useEffect(() => {
    setIsSupported(browserSupportsSpeechRecognition)
  }, [browserSupportsSpeechRecognition])

  const startListening = useCallback(() => {
    resetTranscript()
    SpeechRecognition.startListening({ continuous: true, language })
  }, [language, resetTranscript])

  const stopListening = useCallback(() => {
    SpeechRecognition.stopListening()
    if (transcript && onResult) {
      onResult(transcript)
    }
  }, [transcript, onResult])

  const toggleListening = useCallback(() => {
    if (listening) {
      stopListening()
    } else {
      startListening()
    }
  }, [listening, startListening, stopListening])

  return {
    transcript,
    listening,
    isSupported,
    startListening,
    stopListening,
    toggleListening,
    resetTranscript,
  }
}

export function useVoiceOutput() {
  const [isSpeaking, setIsSpeaking] = useState(false)
  const [isSupported, setIsSupported] = useState(true)

  useEffect(() => {
    setIsSupported('speechSynthesis' in window)
  }, [])

  const speak = useCallback((text: string, lang = 'ja-JP') => {
    if (!('speechSynthesis' in window)) return

    // Cancel any ongoing speech
    window.speechSynthesis.cancel()

    const utterance = new SpeechSynthesisUtterance(text)
    utterance.lang = lang
    utterance.rate = 1.0
    utterance.pitch = 1.0

    utterance.onstart = () => setIsSpeaking(true)
    utterance.onend = () => setIsSpeaking(false)
    utterance.onerror = () => setIsSpeaking(false)

    window.speechSynthesis.speak(utterance)
  }, [])

  const stop = useCallback(() => {
    if ('speechSynthesis' in window) {
      window.speechSynthesis.cancel()
      setIsSpeaking(false)
    }
  }, [])

  return {
    speak,
    stop,
    isSpeaking,
    isSupported,
  }
}
