import { useEffect, useState } from 'react';
import { initSocket, getSocket, disconnectSocket } from '../socket';

export const useSocket = () => {
  const [socket, setSocket] = useState(null);

  useEffect(() => {
    const socketIo = initSocket();
    setSocket(socketIo);
  }, []);

  return socket;
};