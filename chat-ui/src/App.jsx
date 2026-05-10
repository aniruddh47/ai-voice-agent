import React, { useState, useEffect, useRef, useCallback, useMemo } from 'react'
import LoadingScreen from './components/LoadingScreen'
import ChatInterface from './components/ChatInterface'
import VoicePanel from './components/VoicePanel'
import CallControls from './components/CallControls'

const API_PORT = 5000

function App() {
  const [isLoading, setIsLoading] = useState(true)
  const [callActive, setCallActive] = useState(false)
  const [messages, setMessages] = useState([])
  const [isListening, setIsListening] = useState(false)
  const [isProcessing, setIsProcessing] = useState(false)
  const [isMicActive, setIsMicActive] = useState(false)
  const [micStatus, setMicStatus] = useState('')
  const [apiReady, setApiReady] = useState(false)
  const [activeApiBaseUrl, setActiveApiBaseUrl] = useState(`http://localhost:${API_PORT}`)
  const [sessionId, setSessionId] = useState(null)
  
  const recognitionRef = useRef(null)
  const mediaRecorderRef = useRef(null)
  const audioChunksRef = useRef([])
  const lockedVoiceRef = useRef(null)
  const isSpeakingRef = useRef(false)
  const speechQueueRef = useRef([])
  const timeoutIdRef = useRef(null)

  const apiCandidates = useMemo(() => {
    const host = window.location.hostname || 'localhost'
    const candidates = [
      `http://${host}:${API_PORT}`,
      `http://localhost:${API_PORT}`,
      `http://127.0.0.1:${API_PORT}`
    ]
    return [...new Set(candidates)]
  }, [])

  // Load or create chat session
  const initializeOrLoadSession = useCallback(async (baseUrl) => {
    try {
      // Check if we have a stored session ID
      const storedSessionId = localStorage.getItem('sgu_chat_session_id')
      
      if (storedSessionId) {
        // Try to load existing session
        try {
          const response = await fetch(`${baseUrl}/api/chat-history/${storedSessionId}`)
          if (response.ok) {
            const data = await response.json()
            // Load previous messages
            if (data.messages && data.messages.length > 0) {
              const loadedMessages = data.messages.map(msg => ({
                sender: msg.role === 'user' ? 'user' : 'ai',
                text: msg.content,
                timestamp: new Date(msg.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
              }))
              setMessages(loadedMessages)
            }
            setSessionId(storedSessionId)
            console.log(`✅ Loaded existing session: ${storedSessionId}`)
            return storedSessionId
          }
        } catch (err) {
          console.warn('⚠️ Failed to load existing session, creating new one')
        }
      }
      
      // Create new session
      const response = await fetch(`${baseUrl}/api/chat-history/new`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' }
      })
      
      if (response.ok) {
        const data = await response.json()
        const newSessionId = data.session_id
        localStorage.setItem('sgu_chat_session_id', newSessionId)
        setSessionId(newSessionId)
        console.log(`✅ Created new session: ${newSessionId}`)
        return newSessionId
      }
    } catch (err) {
      console.error('❌ Error initializing session:', err)
    }
    
    return null
  }, [])

  const checkApiHealth = useCallback(async () => {
    for (const baseUrl of apiCandidates) {
      try {
        const healthResponse = await fetch(`${baseUrl}/api/health`)
        if (healthResponse.ok) {
          setActiveApiBaseUrl(baseUrl)
          setApiReady(true)
          console.log(`API Server connected at ${baseUrl}`)
          
          // Initialize session when API becomes available
          if (!sessionId) {
            await initializeOrLoadSession(baseUrl)
          }
          
          return baseUrl
        }
      } catch (err) {
        // Try next candidate URL.
      }
    }

    setApiReady(false)
    return null
  }, [apiCandidates, sessionId, initializeOrLoadSession])

  // Initialize app and check API
  useEffect(() => {
    const initApp = async () => {
      // Check API once on initial load
      const baseUrl = await checkApiHealth()
      
      // Initialize session after API check if healthy
      if (baseUrl && !sessionId) {
        await initializeOrLoadSession(baseUrl)
      } else if (!baseUrl) {
        console.error('⚠️ API Server not available on initial check')
      }

      // Initialize Web Speech API with handlers defined ONCE
      const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition
      if (SpeechRecognition) {
        recognitionRef.current = new SpeechRecognition()
        const recognition = recognitionRef.current
        recognition.continuous = false
        recognition.interimResults = true
        recognition.lang = 'en-US'

        // ✅ Define handlers ONCE during initialization (not on every toggle)
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
            if (transcript.trim()) {
              // Send actual transcript to backend
              console.log('✅ Final transcript:', transcript)
              setMicStatus('Processing...')
              setIsListening(false)
              sendMessage(transcript.trim())
            } else {
              console.log('⚠️ Empty transcript, ready for next input')
              setMicStatus('')
              setIsListening(false)
            }
          }
        }

        recognition.onerror = (event) => {
          console.error('❌ Speech recognition error:', event.error)
          // ✅ CRITICAL: Abort the recognition to clean up state
          recognition.abort()
          setIsListening(false)
          setMicStatus(`Error: ${event.error}`)
          
          // Clear timeout if it was waiting
          if (timeoutIdRef.current) {
            clearTimeout(timeoutIdRef.current)
            timeoutIdRef.current = null
          }
          
          // Auto-clear error message after 3 seconds
          setTimeout(() => setMicStatus(''), 3000)
        }

        recognition.onend = () => {
          console.log('🎤 Listening ended')
          setIsListening(false)
          
          // ✅ Clear timeout when listening ends
          if (timeoutIdRef.current) {
            clearTimeout(timeoutIdRef.current)
            timeoutIdRef.current = null
          }
        }
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

    // Keep checking API health so banner clears automatically
    const healthTimer = setInterval(async () => {
      const baseUrl = await checkApiHealth()
      // Initialize session if API just became available
      if (baseUrl && !sessionId) {
        await initializeOrLoadSession(baseUrl)
      }
    }, 5000)

    // Cleanup on unmount
    return () => {
      clearInterval(healthTimer)
      // Abort recognition if still active
      if (recognitionRef.current) {
        try {
          recognitionRef.current.abort()
        } catch (e) {
          // Ignore abort errors
        }
      }
      // Clear any pending timeout
      if (timeoutIdRef.current) {
        clearTimeout(timeoutIdRef.current)
      }
    }
  }, [checkApiHealth, initializeOrLoadSession, sessionId])

  const handleStartCall = async () => {
    setCallActive(true)
    
    // If no messages yet, add welcome message
    if (messages.length === 0) {
      const welcomeMsg = "Hello! Welcome to SGU Admission Counselor. How can I help you today?"
      setMessages([
        {
          sender: 'ai',
          text: welcomeMsg,
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
        }
      ])
    }
    
    setIsMicActive(true)
  }

  const handleEndCall = () => {
    // ✅ Properly clean up recognition
    if (recognitionRef.current) {
      try {
        recognitionRef.current.abort()
      } catch (e) {
        // Ignore abort errors
      }
    }
    
    // ✅ Clear any pending timeout
    if (timeoutIdRef.current) {
      clearTimeout(timeoutIdRef.current)
      timeoutIdRef.current = null
    }
    
    setCallActive(false)
    // Note: Don't clear messages - they're now persisted
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
      // Refresh API status before making the request
      await checkApiHealth()

      const payload = { message: userMessage }
      if (sessionId) {
        payload.session_id = sessionId
      }

      const response = await fetch(`${activeApiBaseUrl}/api/chat`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(payload)
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
      setApiReady(false)
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

    try {
      setIsListening(true)
      setMicStatus('Recording audio...')
      audioChunksRef.current = []

      const recognition = recognitionRef.current

      // ✅ CRITICAL: Ensure we start fresh by aborting any previous session
      recognition.abort()

      // ✅ Small delay to ensure abort completes before restarting
      await new Promise(resolve => setTimeout(resolve, 100))

      // ✅ Now start listening fresh
      recognition.start()
      console.log('✅ Recognition started cleanly')

      // ✅ Set timeout for "no-speech" scenarios (15 seconds is browser default)
      timeoutIdRef.current = setTimeout(() => {
        if (isListening && recognitionRef.current) {
          console.warn('⏱️ Timeout: No speech detected after 15 seconds, stopping')
          recognitionRef.current.abort()
        }
      }, 15000)
    } catch (err) {
      console.error('❌ Error starting recognition:', err)
      setIsListening(false)
      setMicStatus(`Failed to start: ${err.message}`)
      
      // ✅ Try to abort and cleanup on error
      if (recognitionRef.current) {
        try {
          recognitionRef.current.abort()
        } catch (e) {
          // Ignore abort errors
        }
      }
      
      // Clear timeout
      if (timeoutIdRef.current) {
        clearTimeout(timeoutIdRef.current)
        timeoutIdRef.current = null
      }
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
          ⚠️ API Server not connected. Backend is starting or unavailable.
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