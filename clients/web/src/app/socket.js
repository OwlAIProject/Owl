'use client';
import io from 'socket.io-client';

let socket;

export const initSocket = (token) => {
  if (!socket) {
    socket = io(process.env.UNTITLEDAI_API_URL || '/', {
        path: '/api/socket',
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
