'use client';
import { useState, useEffect } from 'react';
import { useSocket } from './useSocket'; 

export const useAudioRecorder = (isRecording, captureUUID) => {
  const socket = useSocket();
  const [audioContext, setAudioContext] = useState(null);
  const [mediaStream, setMediaStream] = useState(null);
  const [scriptProcessor, setScriptProcessor] = useState(null);

  useEffect(() => {
    const startRecording = async () => {
      const sampleRate = 16000; 
      const audioCtx = new (window.AudioContext || window.webkitAudioContext)({
        sampleRate: sampleRate,
      });
      const processor = audioCtx.createScriptProcessor(256, 1, 1);
      setAudioContext(audioCtx);
      setScriptProcessor(processor);

      try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        setMediaStream(stream);
        const source = audioCtx.createMediaStreamSource(stream);
        source.connect(processor);
        processor.connect(audioCtx.destination); 

        processor.onaudioprocess = (e) => {
          if (!isRecording) return;

          const inputData = e.inputBuffer.getChannelData(0);
          const buffer = new Int16Array(inputData.length);
          for (let i = 0; i < inputData.length; i++) {
            buffer[i] = inputData[i] * 0x7FFF; // Convert float32 to int16
          }
          socket.emit('audio_data', buffer.buffer, "web", captureUUID, 'wav');
        };
      } catch (error) {
        console.error("Error accessing the microphone: ", error);
      }
    };

    if (isRecording && captureUUID) {
      startRecording();
    } else {
      scriptProcessor?.disconnect();
      audioContext?.close();
      mediaStream?.getTracks().forEach(track => track.stop());
    }

    return () => {
      scriptProcessor?.disconnect();
      audioContext?.close();
      mediaStream?.getTracks().forEach(track => track.stop());
    };
  }, [isRecording, captureUUID]); 

};
