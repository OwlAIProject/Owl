import { useState, useEffect } from 'react';

export const useLocationTracker = (isActive, captureUUID, updateInterval = 10000) => {
  useEffect(() => {
    let intervalId;

    const postLocation = async (latitude, longitude) => {
      try {
        const response = await fetch('/api/capture/location', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            capture_uuid: captureUUID,
            latitude,
            longitude,
          }),
        });
        const data = await response.json();
        console.log('Location posted:', data);
      } catch (error) {
        console.error('Error posting location:', error);
      }
    };

    const updateLocation = () => {
      if (!navigator.geolocation) {
        console.error("Geolocation is not supported by this browser.");
        return;
      }

      navigator.geolocation.getCurrentPosition(
        (position) => {
          const { latitude, longitude } = position.coords;
          console.log(`Capture UUID: ${captureUUID}, Latitude: ${latitude}, Longitude: ${longitude}`);
          postLocation(latitude, longitude);
        },
        (error) => {
          console.error("Error getting location: ", error);
        }
      );
    };

    if (isActive) {
      updateLocation();
      intervalId = setInterval(updateLocation, updateInterval);
    }

    return () => {
      if (intervalId) clearInterval(intervalId);
    };
  }, [isActive, captureUUID, updateInterval]);

};