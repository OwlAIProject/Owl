import { useEffect, useState } from 'react';
import { initSocket, getSocket, disconnectSocket } from '../socket';

export const useSocket = () => {
  const [socket, setSocket] = useState(null);

  useEffect(() => {
    const initializeSocket = async () => {
        try {
          const response = await fetch(`/api/tokens`, {
            cache: 'no-store'
          });
          if (!response.ok) {
            throw new Error('Failed to fetch tokens');
          }
          const data = await response.json();
          const socketIo = initSocket(data.OWL_USER_CLIENT_TOKEN);
          setSocket(socketIo);
        } catch (error) {
          console.error(error);
        }
      };
      initializeSocket();

  }, []);

  return socket;
};