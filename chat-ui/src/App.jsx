import React, { useState, useEffect, useRef } from 'react'
import LoadingScreen from './components/LoadingScreen'
import ChatInterface from './components/ChatInterface'
import VoicePanel from './components/VoicePanel'
import CallControls from './components/CallControls'

const API_BASE_URL = 'http://localhost:5000'

function App() {
  const [isLoading, setIsLoading] = useState(true)
  const [callActive, setCallActive] = useState(false)
  const [messages, setMessages] = useState([])
  const [isListening, setIsListening] = useState(false)
  const [isProcessing, setIsProcessing] = useState(false)
  const [isMicActive, setIsMicActive] = useState(false)
  const [micStatus, setMicStatus] = useState('')
  const [apiReady, setApiReady] = useState(false)
  
  const recognitionRef = useRef(null)
  const mediaRecorderRef = useRef(null)
  const audioChunksRef = useRef([])
  const lockedVoiceRef = useRef(null)
  const isSpeakingRef = useRef(false)
  const speechQueueRef = useRef([])

  // Initialize app and check API
  useEffect(() => {
    const initApp = async () => {
      try {
        // Check API health
        const healthResponse = await fetch(`${API_BASE_URL}/api/health`)
        if (healthResponse.ok) {
          setApiReady(true)
          console.log('✅ API Server connected')
        }
      } catch (err) {
        console.error('⚠️ API Server not available:', err)
        setApiReady(false)
      }

      // Initialize Web Speech API
      const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition
      if (SpeechRecognition) {
        recognitionRef.current = new SpeechRecognition()
        recognitionRef.current.continuous = false
        recognitionRef.current.interimResults = true
        recognitionRef.current.lang = 'en-US'
      }

      // Initialize and lock a single voice for TTS
      const synth = window.speechSynthesis
      if (synth) {
        // Wait for voices to load
        const loadVoices = () => {
          const voices = synth.getVoices()
          if (voices.length > 0 && !lockedVoiceRef.current) {
            // Lock to FIRST female voice, or first voice available
            const femaleVoice = voices.find(v => 
              v.name.toLowerCase().includes('female') || 
              v.name.toLowerCase().includes('woman') ||
              v.name.toLowerCase().includes('google us english female')
            )
            lockedVoiceRef.current = femaleVoice || voices[0]
            console.log(`🎙️ Voice locked: ${lockedVoiceRef.current.name}`)
          }
        }
        
        // Load voices immediately and when they change
        loadVoices()
        synth.onvoiceschanged = loadVoices
      }

      // Simulate 2-second loading
      setTimeout(() => {
        setIsLoading(false)
      }, 2000)
    }

    initApp()
  }, [])

  const handleStartCall = async () => {
    setCallActive(true)
    setMessages([])
    setIsMicActive(true)

    // Add welcome message
    const welcomeMsg = "Hello! Welcome to SGU Admission Counselor. How can I help you today?"
    setMessages([
      {
        sender: 'ai',
        text: welcomeMsg,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
      }
    ])
  }

  const handleEndCall = () => {
    setCallActive(false)
    setMessages([])
    setIsListening(false)
    setIsProcessing(false)
    setIsMicActive(false)
    setMicStatus('')
  }

  const sendMessage = async (userMessage) => {
    if (!userMessage.trim()) return

    // Add user message to chat
    const userMsg = {
      sender: 'user',
      text: userMessage,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    }

    setMessages(prev => [...prev, userMsg])
    setIsProcessing(true)

    try {
      const response = await fetch(`${API_BASE_URL}/api/chat`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ message: userMessage })
      })

      if (!response.ok) {
        throw new Error('API request failed')
      }

      const data = await response.json()
      const aiResponse = data.response || 'Sorry, I am having trouble at the moment.'

      // Add AI response
      setMessages(prev => [
        ...prev,
        {
          sender: 'ai',
          text: aiResponse,
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
        }
      ])

      // 🎙️ SPEAK THE RESPONSE COMPLETELY AND WAIT FOR IT
      await speakResponse(aiResponse)
      console.log('✅ Response fully spoken, ready for next input')
    } catch (err) {
      console.error('❌ API Error:', err)
      const errorMsg = 'I am having trouble connecting to the server. Please try again.'
      setMessages(prev => [
        ...prev,
        {
          sender: 'ai',
          text: errorMsg,
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
        }
      ])
      await speakResponse(errorMsg)
    } finally {
      setIsProcessing(false)
    }
  }

  const speakResponse = async (text) => {
    // Wait if already speaking
    while (isSpeakingRef.current) {
      await new Promise(resolve => setTimeout(resolve, 100))
    }

    // Queue this speech
    return new Promise((resolve) => {
      const synth = window.speechSynthesis
      
      // Don't interrupt - just queue if already speaking
      if (synth.speaking) {
        speechQueueRef.current.push(text)
        resolve()
        return
      }

      isSpeakingRef.current = true

      // Create utterance
      const utterance = new SpeechSynthesisUtterance(text)
      
      // Use LOCKED voice (no random fallbacks)
      if (lockedVoiceRef.current) {
        utterance.voice = lockedVoiceRef.current
      }

      // Configure speech parameters
      utterance.rate = 0.95        // Slightly slower for clarity
      utterance.pitch = 1.0        // Normal pitch
      utterance.volume = 1.0       // Full volume
      utterance.lang = 'en-US'

      // Handle speech start
      utterance.onstart = () => {
        console.log('🎙️ Speaking...')
      }

      // Handle speech completion
      utterance.onend = () => {
        console.log('✅ Speech complete')
        isSpeakingRef.current = false

        // Check if there's queued speech
        if (speechQueueRef.current.length > 0) {
          const nextText = speechQueueRef.current.shift()
          speakResponse(nextText).then(resolve)
        } else {
          resolve()
        }
      }

      // Handle errors
      utterance.onerror = (event) => {
        console.error('❌ Speech error:', event.error)
        isSpeakingRef.current = false
        resolve()
      }

      // Start speaking the full text (no cancellation)
      synth.speak(utterance)
    })
  }

  const handleMicToggle = async () => {
    // Don't start if already processing, speaking, or listening
    if (isListening || isProcessing || isSpeakingRef.current || !recognitionRef.current) {
      console.log('⏸️ Mic action blocked: already processing/speaking')
      return
    }

    // Start listening
    setIsListening(true)
    setMicStatus('Recording audio...')
    audioChunksRef.current = []

    const recognition = recognitionRef.current

    recognition.onstart = () => {
      console.log('🎤 Listening started')
    }

    recognition.onresult = (event) => {
      let transcript = ''
      
      for (let i = event.resultIndex; i < event.results.length; i++) {
        transcript += event.results[i][0].transcript
      }

      // Show interim results
      if (transcript) {
        setMicStatus(`Heard: "${transcript}"`)
      }

      // If final result
      if (event.results[event.results.length - 1].isFinal) {
        setIsListening(false)
        
        if (transcript.trim()) {
          // Send actual transcript to backend
          console.log('✅ Final transcript:', transcript)
          setMicStatus('Processing...')
          sendMessage(transcript.trim())
        } else {
          console.log('⚠️ Empty transcript, ready for next input')
          setMicStatus('')
        }
      }
    }

    recognition.onerror = (event) => {
      console.error('❌ Speech recognition error:', event.error)
      setIsListening(false)
      setMicStatus(`Error: ${event.error}`)
      setTimeout(() => setMicStatus(''), 2000)
    }

    recognition.onend = () => {
      console.log('🎤 Listening ended')
      setIsListening(false)
    }

    // Start listening
    try {
      recognition.start()
    } catch (err) {
      console.error('Error starting recognition:', err)
      setIsListening(false)
    }
  }

  if (isLoading) {
    return <LoadingScreen />
  }

  return (
    <div className="flex h-screen bg-gray-100">
      {/* API Status Indicator */}
      {!apiReady && (
        <div className="fixed top-0 left-0 right-0 bg-yellow-500 text-white px-4 py-2 text-sm z-40">
          ⚠️ API Server not connected. Run: python api_server.py
        </div>
      )}

      {/* Chat Interface - Left */}
      <div className="flex-1 flex flex-col overflow-hidden">
        <ChatInterface messages={messages} isTyping={isProcessing} />
        <CallControls
          callActive={callActive}
          onStartCall={handleStartCall}
          onEndCall={handleEndCall}
        />
      </div>

      {/* Voice Panel - Right */}
      <div className="w-80 border-l border-gray-300 overflow-hidden">
        <VoicePanel
          isListening={isListening}
          isProcessing={isProcessing}
          isMicActive={isMicActive && callActive}
          onMicToggle={handleMicToggle}
          micStatus={micStatus}
          callActive={callActive}
        />
      </div>
    </div>
  )
}

export default App