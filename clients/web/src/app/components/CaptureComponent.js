'use client';

import React, { useState } from 'react';
import { useAudioRecorder } from '../hooks/useAudioRecorder';
import { useLocationTracker } from '../hooks/useLocationTracker';
import { useBluetoothAudioStreamer } from '../hooks/useBluetoothAudioStreamer';
import { useSocket } from '../hooks/useSocket';
import { FiBluetooth, FiMic, FiSquare } from 'react-icons/fi';
import { v4 as uuidv4 } from 'uuid';

const generateHexUUID = () => {
  const uuid = uuidv4();
  const hexFormatUUID = uuid.replace(/-/g, '').toLowerCase();
  return hexFormatUUID;
};

const CaptureComponent = () => {
  const socket = useSocket();
  const [isRecording, setIsRecording] = useState(false);
  const [isBluetoothActive, setIsBluetoothActive] = useState(false);
  const [captureUUID, setCaptureUUID] = useState('');

  const toggleBluetooth = () => {
    if (isBluetoothActive) {
      setIsBluetoothActive(false);
      setCaptureUUID('');
      socket.emit('finish_audio', captureUUID);
    } else {
      const newCaptureUUID = generateHexUUID();
      setCaptureUUID(newCaptureUUID);
      setIsBluetoothActive(true);
    }
  };

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

  useBluetoothAudioStreamer(isBluetoothActive, captureUUID);

  useAudioRecorder(isRecording, captureUUID);

  useLocationTracker(isRecording || isBluetoothActive, captureUUID);

  return (
    <div className="fixed top-5 right-5 flex flex-col space-y-2 bg-black bg-opacity-50 p-3 rounded-lg z-50">
      <button
        className={`p-3 rounded-full ${isRecording ? 'bg-red-500' : 'bg-green-500'} text-white flex items-center justify-center`}
        onClick={toggleRecording}
      >
        {isRecording ? <FiSquare size={24} /> : <FiMic size={24} />}
      </button>
      <button
        onClick={toggleBluetooth}
        className={`p-3 rounded-full ${isBluetoothActive ? 'bg-blue-500' : 'bg-gray-500'} text-white flex items-center justify-center`}
      >
        {isBluetoothActive ? <FiSquare size={24} /> : <FiBluetooth size={24} />}
      </button>
    </div>
  );
};

export default CaptureComponent;