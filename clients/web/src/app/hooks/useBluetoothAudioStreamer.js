import { useEffect, useState } from 'react';
import { useSocket } from './useSocket';
import { FrameSequencer } from '../utils/frameSequencer';

export const useBluetoothAudioStreamer = (isActive, captureUUID) => {
  const socket = useSocket();
  const [device, setDevice] = useState(null);

  const disconnectDevice = async () => {
    if (device && device.gatt.connected) {
      console.log("Disconnecting from Bluetooth device.");
      await device.gatt.disconnect();
      setDevice(null);
    }
  };

  useEffect(() => {
    if (!isActive) {
      disconnectDevice();
      return;
    }

    let frameSequencer = new FrameSequencer();

    async function connectToBLEDevice() {
      try {
        const device = await navigator.bluetooth.requestDevice({
          filters: [{services: ["03d5d5c4-a86c-11ee-9d89-8f2089a49e7e"]}]
        });
        setDevice(device);
        const server = await device.gatt.connect();
        const service = await server.getPrimaryService("03d5d5c4-a86c-11ee-9d89-8f2089a49e7e");
        const characteristic = await service.getCharacteristic("b189a505-a86c-11ee-a5fb-8f2089a49e7e");

        characteristic.addEventListener('characteristicvaluechanged', (event) => {
          let value = event.target.value;
          let frame = frameSequencer.add(value);
          if (frame) {
            socket.emit('audio_data', new Uint8Array(frame), "web", captureUUID, 'aac');
          }
        });

        await characteristic.startNotifications();
      } catch (error) {
        console.error("Bluetooth Audio Streaming Error: ", error);
      }
    }

    connectToBLEDevice();

    return () => {
      disconnectDevice();
    };
  }, [isActive, captureUUID, socket]);

  useEffect(() => {
    return () => {
      disconnectDevice();
    };
  }, []);
};
