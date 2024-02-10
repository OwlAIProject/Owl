'use client';

import React, { useState, useEffect } from 'react';

const CountUpTimer = ({ startTime }) => {
  const [elapsedTime, setElapsedTime] = useState(0);

  useEffect(() => {
    const utcStartTime = new Date(`${startTime}Z`); // Append 'Z' to indicate UTC

    const updateElapsedTime = () => {
      const now = new Date(); 
      const newElapsedTime = now - utcStartTime;
      setElapsedTime(newElapsedTime);
    };

    const timerId = setInterval(updateElapsedTime, 1000);

    updateElapsedTime();

    return () => clearInterval(timerId);
  }, [startTime]);

  const formatElapsedTime = (timeInMilliseconds) => {
    const totalSeconds = Math.floor(timeInMilliseconds / 1000);
    const hours = Math.floor(totalSeconds / 3600);
    const minutes = Math.floor((totalSeconds % 3600) / 60);
    const seconds = totalSeconds % 60;

    return [hours, minutes, seconds]
      .map(val => val < 10 ? `0${val}` : val) 
      .join(':');
  };

  return (
    <div className="text-sm font-medium text-white bg-blue-600 rounded-full px-4 py-1 animate-pulse">
      {formatElapsedTime(elapsedTime)}
    </div>
  );
};


export default CountUpTimer;