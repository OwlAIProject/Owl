/*
 * Header format:
 *
 *          Bit
 *  Byte     7  4 3  0
 *          +----+----+
 *    0     |xxxx|ffff|
 *          +----+----+
 * 
 *          +----+----+
 *    1     |nnnn|ssss|
 *          +----+----+
 * 
 *  xxxx    Reserved
 *  ffff    Inter-frame sequence number (complete frame)
 *  nnnn    Number of BLE packets in this frame
 *  ssss    Sequence number for this frame (intra-frame), [0,n)
 */

#include <Arduino.h>
#include <I2S.h>
#include <BLEDevice.h>
#include <BLEServer.h>
#include "esp_aac_enc.h"
#include "esp_audio_enc_def.h"
#include "esp_audio_def.h"

constexpr const char *ServiceID = "03d5d5c4-a86c-11ee-9d89-8f2089a49e7e";
constexpr const char *TxID = "b189a505-a86c-11ee-a5fb-8f2089a49e7e";
constexpr const char *RxID = "ff000353-a872-11ee-b751-8f2089a49e7e";

constexpr const size_t HeaderSize = 2;    // sequence numbers
constexpr const size_t MaxSendSize = 182; // match iOS MTU size (185 - 3) for best send rate
static BLECharacteristic *s_tx = nullptr;
static bool s_is_connected = false;
static uint8_t s_output_buffer[MaxSendSize];
static uint8_t s_interframe_seqno = 0;
static uint8_t s_intraframe_seqno = 0;

constexpr const int SampleRate = 16000;
static int8_t s_audio_buffer[2048];

static esp_aac_enc_config_t s_encoder_config;
static void *s_encoder_handle = nullptr;
static int s_frame_in_bytes = 0;
static int s_frame_out_bytes = 0;
static uint8_t *s_recording_buffer = nullptr;
static uint8_t *s_input_frame = nullptr;
static uint8_t *s_compressed_frame = nullptr;

class server_handler: public BLEServerCallbacks
{
  void onConnect(BLEServer *server)
  {
    s_is_connected = true;
    Serial.println("Connected");
  }

  void onDisconnect(BLEServer *server)
  {
    s_is_connected = false;
    Serial.println("Disconnected");
    BLEDevice::startAdvertising();
  }
};

class message_handler: public BLECharacteristicCallbacks
{
  void onWrite(BLECharacteristic* pCharacteristic, esp_ble_gatts_cb_param_t* param)
  {
    // Currently unused
  }
};

static void setup_microphone()
{
  I2S.setAllPins(-1, 42, 41, -1, -1);
  if (!I2S.begin(PDM_MONO_MODE, SampleRate, 16))
  {
      while (true)
      {
        Serial.println("Failed to initialize I2S for audio recording!");
        delay(1000);
      }
  }
}

static void setup_aac_encoder()
{
  // Set encoder configuration
  s_encoder_config = ESP_AAC_ENC_CONFIG_DEFAULT();
  s_encoder_config.sample_rate = 16000;
  s_encoder_config.channel = 1;
  s_encoder_config.bitrate = 90000;
  s_encoder_config.adts_used = 1;

  // Create encoder
  if (0 != esp_aac_enc_open(&s_encoder_config, sizeof(esp_aac_enc_config_t), &s_encoder_handle))
  {
    Serial.println("Error: Unable to create encoder");
    return;
  }
  
  // Get size of input and output frames
  esp_aac_enc_get_frame_size(s_encoder_handle, &s_frame_in_bytes, &s_frame_out_bytes);
  Serial.printf("Frame in: %d bytes\n", s_frame_in_bytes);
  Serial.printf("Frame out: %d bytes\n", s_frame_out_bytes);
      
  // Allocate audio buffers
  s_recording_buffer = (uint8_t *) ps_calloc(s_frame_in_bytes, sizeof(uint8_t));
  s_input_frame = (uint8_t *) ps_calloc(s_frame_in_bytes, sizeof(uint8_t));
  s_compressed_frame = (uint8_t *) ps_calloc(s_frame_out_bytes, sizeof(uint8_t));
}

void setup()
{
  pinMode(D0, INPUT_PULLUP);

  Serial.begin(115200);

  BLEDevice::init("xiao_esp32s3_sense");
  BLEServer *server = BLEDevice::createServer();
  BLEService *service = server->createService(ServiceID);
  s_tx = service->createCharacteristic(
    TxID,
    BLECharacteristic::PROPERTY_NOTIFY
  );
  BLECharacteristic *rx = service->createCharacteristic(
    RxID,
    BLECharacteristic::PROPERTY_WRITE_NR
  );
  rx->setCallbacks(new message_handler());
  server->setCallbacks(new server_handler());
  service->start();

  BLEAdvertising *advertising = BLEDevice::getAdvertising();
  advertising->addServiceUUID(ServiceID);
  advertising->setScanResponse(true);
  advertising->setMinPreferred(0x06);
  advertising->setMinPreferred(0x12);
  advertising->setMinInterval(0x20);
  advertising->setMaxInterval(0x40);
  BLEDevice::startAdvertising();

  Serial.printf("MTU size: %d bytes\n", BLEDevice::getMTU());

  setup_aac_encoder();
  setup_microphone();

  Serial.println("Setup completed");
}

void loop()
{
  if (!s_is_connected) {
    delay(50); // Wait for a connection
    return;
  }
  
  unsigned long t0 = millis();

  size_t bytes_recorded = 0;
  esp_i2s::i2s_read(esp_i2s::I2S_NUM_0, s_recording_buffer, s_frame_in_bytes, &bytes_recorded, portMAX_DELAY);
  if (0 == bytes_recorded)
  {
    Serial.println("Recording failed!");
    return;
  }

  unsigned long t1 = millis();
  //Serial.printf("Recording took: %lu\n", t1 - t0);

  // Encode process
  const uint8_t *recording = s_recording_buffer;
  const uint8_t *recording_end = s_recording_buffer + bytes_recorded;
  esp_audio_enc_in_frame_t in_frame = { 0 };
  esp_audio_enc_out_frame_t out_frame = { 0 };
  in_frame.buffer = s_input_frame;
  in_frame.len = s_frame_in_bytes;
  out_frame.buffer = s_compressed_frame;
  out_frame.len = s_frame_out_bytes;

  while (recording < recording_end)
  {
    unsigned long t0 = millis();

    // Don't read past end of input buffer and pad frame with zeros if need be
    int bytes_remaining = recording_end - recording;
    int chunk_bytes = min(s_frame_in_bytes, bytes_remaining);
    memcpy(s_input_frame, recording, chunk_bytes);
    if (chunk_bytes < s_frame_in_bytes)
    {
      memset(s_input_frame + chunk_bytes, 0, s_frame_in_bytes - chunk_bytes);
    }
    recording += chunk_bytes;

    if (ESP_AUDIO_ERR_OK != esp_aac_enc_process(s_encoder_handle, &in_frame, &out_frame))
    {
      Serial.println("Audio encoder process failed.");
      return;
    }

    //Serial.printf("%d -> %d\n", s_frame_in_bytes, out_frame.encoded_bytes);

    unsigned long t1 = millis();

    {
      // Compute number of packets to send out this frame
      size_t max_chunk_size = MaxSendSize - HeaderSize;
      size_t num_packets = out_frame.encoded_bytes / max_chunk_size + ((out_frame.encoded_bytes % max_chunk_size) ? 1 : 0);

      // Header: inter-frame sequence number
      s_output_buffer[0] = s_interframe_seqno & 0xf;
      s_intraframe_seqno = 0;

      // Stream out the packets
      size_t bytes_remaining = out_frame.encoded_bytes;
      uint8_t *buffer = (uint8_t *) out_frame.buffer;
      while (bytes_remaining > 0)
      {
        // Header: intra-frame sequence number
        s_output_buffer[1] = (num_packets << 4) | (s_intraframe_seqno & 0xf);

        // Copy into output buffer
        size_t chunk_size = min(max_chunk_size, bytes_remaining);
        size_t packet_size = chunk_size + HeaderSize;
        memcpy(&s_output_buffer[HeaderSize], buffer, chunk_size);
        
        // Send
        s_tx->setValue(s_output_buffer, packet_size);
        s_tx->notify();
        delay(4);

        // Next bytes
        bytes_remaining -= chunk_size;
        buffer += chunk_size;
        s_intraframe_seqno += 1;
      }

      // Frame complete
      s_interframe_seqno += 1;
    }

    unsigned long t2 = millis();
    //Serial.printf("Encoding took: %lu\n", t1 - t0);
    //Serial.printf("Sending took: %lu\n", t2 - t1);
  }
}
