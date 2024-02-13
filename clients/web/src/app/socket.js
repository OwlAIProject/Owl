'use client';
import io from 'socket.io-client';

let socket;

export const initSocket = (token) => {
    if (!socket) {
        const dev = process.env.NODE_ENV !== 'production';
        const backendBaseUrl = dev ? 'http://127.0.0.1:8000' : '/';
        let options = {
            extraHeaders: {
                Authorization: `Bearer ${token}`
            }
        }
        if (!dev) {
            options.path = '/api/socket';
        }
        socket = io(backendBaseUrl, options);
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
