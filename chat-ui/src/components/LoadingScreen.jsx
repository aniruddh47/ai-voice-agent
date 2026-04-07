import React from 'react'

const LoadingScreen = () => {
  return (
    <div className="fixed inset-0 bg-gradient-to-br from-blue-50 to-indigo-100 flex items-center justify-center z-50">
      <div className="text-center">
        <div className="mb-6">
          <div className="inline-flex items-center justify-center w-16 h-16 bg-gradient-to-br from-blue-500 to-indigo-600 rounded-full">
            <div className="w-12 h-12 border-4 border-white border-t-transparent rounded-full animate-spin"></div>
          </div>
        </div>
        <h2 className="text-2xl font-bold text-gray-800 mb-2">SGU Admission Counselor</h2>
        <p className="text-gray-600">Initializing AI Agent...</p>
      </div>
    </div>
  )
}

export default LoadingScreen