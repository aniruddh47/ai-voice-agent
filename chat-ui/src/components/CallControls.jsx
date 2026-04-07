import React from 'react'

const CallControls = ({ callActive, onStartCall, onEndCall }) => {
  return (
    <div className="bg-white border-t border-gray-200 px-6 py-4 flex gap-3">
      {!callActive ? (
        <button
          onClick={onStartCall}
          className="flex-1 bg-gradient-to-r from-green-500 to-green-600 hover:from-green-600 hover:to-green-700 text-white font-bold py-3 px-4 rounded-lg shadow-lg transition-all duration-200 active:scale-95"
        >
          <span className="text-lg mr-2">📞</span>
          Start Call
        </button>
      ) : (
        <>
          <button
            onClick={onEndCall}
            className="flex-1 bg-gradient-to-r from-red-500 to-red-600 hover:from-red-600 hover:to-red-700 text-white font-bold py-3 px-4 rounded-lg shadow-lg transition-all duration-200 active:scale-95"
          >
            <span className="text-lg mr-2">📞</span>
            End Call
          </button>
        </>
      )}
    </div>
  )
}

export default CallControls