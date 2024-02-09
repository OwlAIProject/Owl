#include <Audio.h>
#include <LTE.h>
#include <queue>
#include <deque>
#include <LTEUdp.h>
#include <SDHCI.h>

AudioClass *theAudio;
const int mic_channel_num = 1;
#define APP_LTE_APN "iot.truphone.com"
#define APP_LTE_IP_TYPE (LTE_NET_IPTYPE_V4V6)
#define APP_LTE_AUTH_TYPE (LTE_NET_AUTHTYPE_NONE)
#define APP_LTE_RAT (LTE_NET_RAT_CATM)

// host configuration
char serverAddress[] = "";
int port = 8001;

LTE lteAccess;
LTEUDP udp;

static void audio_attention_cb(const ErrorAttentionParam *atprm) {
  puts("Attention!");

  if (atprm->error_code >= AS_ATTENTION_CODE_WARNING) {

    theAudio->startRecorder();
  }
}

void setup() {
  char apn[LTE_NET_APN_MAXLEN] = APP_LTE_APN;
  LTENetworkAuthType authtype = APP_LTE_AUTH_TYPE;

  Serial.begin(115200);
  while (!Serial)
    ;

  Serial.println("Starting LTE client setup.");

  Serial.println("=========== APN information ===========");
  Serial.print("Access Point Name  : ");
  Serial.println(apn);
  Serial.print("Authentication Type: ");
  Serial.println((authtype == LTE_NET_AUTHTYPE_CHAP) ? "CHAP" : (authtype == LTE_NET_AUTHTYPE_NONE) ? "NONE" : "PAP");

  while (true) {
    if (lteAccess.begin() != LTE_SEARCHING) {
      Serial.println("Could not transition to LTE_SEARCHING.");
      Serial.println("Please check the status of the LTE board.");
      for (;;) {
        sleep(1);
      }
    }

    if (lteAccess.attach(APP_LTE_RAT,
                         apn,
                         "",
                         "",
                         authtype,
                         APP_LTE_IP_TYPE)
        == LTE_READY) {
      Serial.println("attach succeeded.");

      break;
    }
  }

  if (!udp.begin(port)) {
    Serial.println("Failed to start UDP");
    while (true)
      ;
  }

  Serial.println("UDP started.");

  Serial.println("Init Audio Library");
  theAudio = AudioClass::getInstance();
  theAudio->begin(audio_attention_cb);

  Serial.println("Init Audio Recorder");
  theAudio->setRecorderMode(AS_SETRECDR_STS_INPUTDEVICE_MIC, 10, 200 * 1024);

  uint8_t channel = AS_CHANNEL_MONO;
  theAudio->initRecorder(AS_CODECTYPE_MP3, "/mnt/sd0/BIN", AS_SAMPLINGRATE_16000, channel);

  theAudio->startRecorder();

  Serial.println("Rec start!");
}

void loop() {
  static const size_t bufferSize = 4096;
  char buffer[bufferSize];
  uint32_t readSize;
  int err = theAudio->readFrames(buffer, bufferSize, &readSize);

  if (readSize > 0) {
    if (readSize > 0) {
      udp.beginPacket(serverAddress, port);
      udp.write(buffer, readSize);
      udp.endPacket();
    }
  }
}
