'use client';

import React, { useState } from 'react';
import { useAudioRecorder } from '../hooks/useAudioRecorder';
import { useLocationTracker } from '../hooks/useLocationTracker';
import { FiMic, FiSquare } from 'react-icons/fi';
import { useSocket } from '../hooks/useSocket'; 


const generateHexUUID = () => {
  return crypto.randomUUID().replace(/-/g, '').toLowerCase();
};

const CaptureComponent = () => {
  const socket = useSocket();
  const [isRecording, setIsRecording] = useState(false);
  const [captureUUID, setCaptureUUID] = useState('');

  // Start/Stop recording and location tracking
  const toggleRecording = () => {
    if (isRecording) {
      setIsRecording(false);
      setCaptureUUID('');
      socket.emit('finish_audio', captureUUID);
    } else {
      const newCaptureUUID = generateHexUUID();
      setCaptureUUID(newCaptureUUID);
      setIsRecording(true);
    }
  };

  useAudioRecorder(isRecording, captureUUID);

  useLocationTracker(isRecording, captureUUID);

  return (
    <div className="fixed top-5 right-5">
      <button
        className={`p-3 rounded-full ${isRecording ? 'bg-red-500' : 'bg-green-500'} text-white flex items-center`}
        onClick={toggleRecording}
      >
        {isRecording ? <FiSquare size={24} /> : <FiMic size={24} />}
        <span className="ml-2">{isRecording ? 'Stop Recording' : 'Start Recording'}</span>
      </button>
    </div>
  );
};

export default CaptureComponent;