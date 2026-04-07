import React, { useEffect, useRef } from 'react'

const ChatInterface = ({ messages, isTyping }) => {
  const messagesEndRef = useRef(null)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages, isTyping])

  return (
    <div className="flex flex-col h-full bg-white">
      {/* Header */}
      <div className="bg-gradient-to-r from-blue-500 to-indigo-600 text-white p-4 shadow-lg">
        <h1 className="text-xl font-bold">Chat with Counselor</h1>
        <p className="text-blue-100 text-sm">SGU Admission Office</p>
      </div>

      {/* Messages Container */}
      <div className="flex-1 overflow-y-auto p-4 bg-gray-50">
        {messages.length === 0 ? (
          <div className="flex items-center justify-center h-full">
            <div className="text-center text-gray-400">
              <div className="text-4xl mb-2">💬</div>
              <p>No messages yet. Start a call to begin!</p>
            </div>
          </div>
        ) : (
          <div className="space-y-4">
            {messages.map((msg, idx) => (
              <div
                key={idx}
                className={`flex ${msg.sender === 'ai' ? 'justify-start' : 'justify-end'}`}
              >
                <div
                  className={`max-w-xs lg:max-w-md px-4 py-2 rounded-lg shadow-sm ${
                    msg.sender === 'ai'
                      ? 'bg-gray-200 text-gray-800 rounded-bl-none'
                      : 'bg-blue-500 text-white rounded-br-none'
                  }`}
                >
                  <p className="text-sm lg:text-base">{msg.text}</p>
                  <p
                    className={`text-xs mt-1 ${
                      msg.sender === 'ai' ? 'text-gray-500' : 'text-blue-100'
                    }`}
                  >
                    {msg.timestamp}
                  </p>
                </div>
              </div>
            ))}

            {/* Typing Indicator */}
            {isTyping && (
              <div className="flex justify-start">
                <div className="bg-gray-200 text-gray-800 px-4 py-3 rounded-lg rounded-bl-none shadow-sm">
                  <div className="flex space-x-2">
                    <div className="w-2 h-2 bg-gray-500 rounded-full animate-pulse"></div>
                    <div className="w-2 h-2 bg-gray-500 rounded-full animate-pulse" style={{ animationDelay: '0.2s' }}></div>
                    <div className="w-2 h-2 bg-gray-500 rounded-full animate-pulse" style={{ animationDelay: '0.4s' }}></div>
                  </div>
                  <p className="text-xs text-gray-500 mt-1">AI is thinking...</p>
                </div>
              </div>
            )}

            <div ref={messagesEndRef} />
          </div>
        )}
      </div>

      {/* Input Area */}
      <div className="border-t border-gray-200 p-4 bg-white">
        <p className="text-xs text-gray-500 text-center">Use the voice panel on the right to speak</p>
      </div>
    </div>
  )
}

export default ChatInterface