import React from 'react'

const VoicePanel = ({
  isListening,
  isProcessing,
  isMicActive,
  onMicToggle,
  micStatus,
  callActive
}) => {
  const getMicIcon = () => {
    if (!callActive) {
      return '🎤'
    }
    if (isListening) {
      return '🎙️'
    }
    if (isProcessing) {
      return '⚙️'
    }
    return '🎤'
  }

  const getStatusColor = () => {
    if (isListening) return 'text-red-500'
    if (isProcessing) return 'text-yellow-500'
    return 'text-green-500'
  }

  return (
    <div className="flex flex-col h-full bg-gradient-to-br from-gray-900 to-gray-800 text-white">
      {/* Header */}
      <div className="p-6 border-b border-gray-700">
        <h2 className="text-xl font-bold">Voice Assistant</h2>
        <p className="text-gray-400 text-sm mt-1">Real-time conversation</p>
      </div>

      {/* Status Section */}
      <div className="flex-1 flex flex-col items-center justify-center px-6 py-8">
        {/* Microphone Button */}
        {callActive ? (
          <div className="mb-8">
            {/* Pulse ring animation when listening */}
            {isListening && (
              <div className="absolute w-24 h-24 bg-red-500 rounded-full animate-pulse opacity-30"></div>
            )}
            
            <button
              onClick={onMicToggle}
              disabled={!callActive}
              className={`relative w-24 h-24 rounded-full font-bold text-2xl transition-all duration-200 shadow-lg hover:shadow-xl active:scale-95 ${
                isListening
                  ? 'bg-red-500 hover:bg-red-600'
                  : isMicActive
                  ? 'bg-blue-500 hover:bg-blue-600'
                  : 'bg-gray-700 hover:bg-gray-600'
              }`}
            >
              {getMicIcon()}
            </button>
          </div>
        ) : (
          <div className="mb-8 text-center">
            <div className="text-5xl mb-4 opacity-50">🎤</div>
            <p className="text-gray-400">Start a call to begin</p>
          </div>
        )}

        {/* Status Text */}
        <div className="text-center mb-6">
          <p className={`text-lg font-semibold ${getStatusColor()}`}>
            {isListening && 'Listening...'}
            {isProcessing && 'Processing...'}
            {!isListening && !isProcessing && callActive && 'Tap to speak'}
            {!callActive && 'Ready'}
          </p>
          {callActive && (
            <p className="text-xs text-gray-400 mt-2">
              {micStatus}
            </p>
          )}
        </div>

        {/* Waveform Visualization (when listening) */}
        {isListening && (
          <div className="flex items-end gap-1 h-16 justify-center mb-6">
            {[...Array(5)].map((_, i) => (
              <div
                key={i}
                className="w-1 bg-gradient-to-t from-red-500 to-red-300 rounded-full"
                style={{
                  height: `${20 + Math.random() * 40}px`,
                  animation: `pulse 0.6s ease-in-out ${i * 0.1}s infinite`
                }}
              ></div>
            ))}
          </div>
        )}

        {/* Device Info */}
        {callActive && (
          <div className="bg-gray-700 rounded-lg p-4 w-full text-xs">
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-gray-400">Microphone:</span>
                <span className="text-green-400">🟢 Connected</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-gray-400">Speaker:</span>
                <span className="text-green-400">🟢 Active</span>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Footer */}
      <div className="p-4 border-t border-gray-700 text-center text-xs text-gray-400">
        <p>Voice powered by Gemini API</p>
      </div>
    </div>
  )
}

export default VoicePanel