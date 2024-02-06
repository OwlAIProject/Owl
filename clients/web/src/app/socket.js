'use client';
import io from 'socket.io-client';

let socket;

export const initSocket = () => {
  const token = process.env.NEXT_PUBLIC_UNTITLEDAI_CLIENT_TOKEN;
  if (!socket) {
    socket = io('http://localhost:8000', {
        extraHeaders: {
            Authorization: `Bearer ${token}`
          }
    });
    console.log('Connecting to socket server');
  }

  return socket;
};

export const getSocket = () => {
  if (!socket) {
    throw new Error('Socket not initialized. Call initSocket(serverUrl) first.');
  }
  return socket;
};

export const disconnectSocket = () => {
  if (socket) {
    socket.disconnect();
    socket = null;
  }
};
