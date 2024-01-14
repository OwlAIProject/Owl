# ESP_AUDIO_CODEC

Espressif Audio Codec (ESP_AUDIO_CODEC) is the official audio encoding and decoding processing module developed by Espressif Systems for SoCs. 

The ESP Audio Encoder provides a common encoder interface that allows you to register multiple encoders, such as AAC, AMR-NB, AMR-WB, ADPCM, G711A, G711, PCM, OPUS. You can create one or multiple encoder handles using the same set of function interfaces, enabling simultaneous encoding. This interface is convenient and easy to use.

The licenses of the third-party copyrights are recorded in [Copyrights and Licenses](http://docs.espressif.com/projects/esp-adf/en/latest/COPYRIGHT.html).

# Features

The ESP Audio Codec supports the following features:   

## Encoder   

AAC     
- AAC low complexity profile encode (AAC-LC)
- Encoding sample rates (Hz): 96000, 88200, 64000, 48000, 44100, 32000, 24000, 22050, 16000, 12000, 11025, 8000    
- Encoding channel num: mono, dual     
- Encoding bit per sample: 16 bits    
- Constant bitrate encoding from 12 Kbps to 160 Kbps    
- Choosing whether to write ADTS header or not   

AMR       
- Encoding narrow band (NB) and wide band (WB)   
- AMRNB encoding at the sampling rate of 8 kHz       
- AMRWB encoding at the sampling rate of 16 kHz     
- Encoding channel num: mono    
- Encoding bit per sample: 16 bits    
- AMRNB encoding bitrate (Kbps): 4.75, 5.15, 5.9, 6.7, 7.4, 7.95, 10.2, 12.2    
- AMRWB encoding bitrate (Kbps): 6.6, 8.85, 12.65, 14.25, 15.85, 18.25, 19.85, 23.05, 23.85      
- Discontinuous transmission (DTX)     

ADPCM   
- Encoding sample rates (Hz): all    
- Encoding channel num: mono, dual    
- Encoding bit per sample: 16 bits    

G711    
- Encoding A-LAW and U-LAW      
- Encoding sample rates (Hz): all    
- Encoding channel num: all    
- Encoding bit per sample: 16 bits    

OPUS    
- Encoding sample rates (Hz): 8000, 12000, 16000, 24000, 48000    
- Encoding channel num: mono, dual    
- Encoding bit per sample: 16 bits    
- Constant bitrate encoding from 20Kbps to 510Kbps      
- Encoding frame duration (ms): 2.5, 5, 10, 20, 40, 60       
- Application mode for VoIP and music       
- Encoding complexity adjustment, from 0 to 10      
- Inband forward error correction (FEC)     
- Discontinuous transmission (DTX)      

# Performance

The following results were obtained through testing with ESP32-S3R8 and internal RAM memory.    

## Encoder 

AAC     
| Sample Rate (Hz)    | Memory (KB) | CPU loading (%)|
|       --            |  --         |     --         |  
|       8000          |  52         |    3.5         | 
|       11025         |  52         |    4.9         | 
|       12000         |  52         |    5.6         | 
|       16000         |  52         |    6.0         | 
|       22050         |  52         |    8.1         | 
|       24000         |  52         |    8.2         | 
|       32000         |  52         |    12.1        | 
|       44100         |  52         |    15.7        | 
|       48000         |  52         |    16.4        | 
|       64000         |  52         |    20.2        | 
|       88200         |  52         |    25.9        | 
|       96000         |  52         |    27.7        |      

Note:       
    The CPU loading values in the table pertain to the mono channel, while the CPU loading for the dual channel is approximately 1.6 times that of the mono channel.   

AMR     
| Type    | Memory (KB)  | CPU loading (%) |
|   --    |  --          |     --          |  
|  AMR-NB |  3.4         |    24.8         | 
|  AMR-WB |  5.8         |    57.6         |     

Note:   
    1) The CPU loading in the table is an average number.       
    2) The CPU loading of AMR is related to the bitrate. The higher the bitrate is set, the higher the CPU loading will be.     

ADPCM     
| Channel | Memory (B)    | CPU loading (%) |
|   --    |  --           |     --          |  
|  mono   |  120          |    < 2          | 
|  dual   |  120          |    < 4          | 

G711     
| Type    | Memory (B)    | CPU loading (%) |
|   --    |  --           |     --          |  
|  G711-A |  40           |    < 4          | 
|  G711-U |  40           |    < 4          | 

Note:   
    The CPU loading in the table is for mono, and the CPU loading of dual is about 2 times that of mono.     

OPUS
| Sample Rate (Hz)     | Memory (KB) | CPU loading (%) |
|       --             |  --         |     --          |  
|       8000           |  43         |    15.9         | 
|       12000          |  43         |    16.7         | 
|       16000          |  43         |    16.8         | 
|       24000          |  43         |    17.8         | 
|       48000          |  43         |    19.9         | 

Note:   
    1) The data in the table is tested under the configuration with mono channel, complexity of 1, VoIP application mode, and a frame duration of 20 ms.    
    2) The dual channel encoding consumes about 13 KB more memory compared to the mono channel.     
    3) The CPU loading for the dual channel is about 1.6 times that of the mono channel.     
    4) The chosen complexity level directly impacts CPU loading, with 1 being the lowest and 10 being the highest.          

#  ESP_AUDIO_CODEC Release and SoC Compatibility

The following table shows the support of ESP_AUDIO_CODEC for Espressif SoCs. The "&#10004;" means supported, and the "&#10006;" means not supported. 

|Chip         |         v1.0.0     |
|:-----------:|:------------------:|
|ESP32        |       &#10004;     |
|ESP32-S2     |       &#10004;     |
|ESP32-C3     |       &#10004;     |
|ESP32-S3     |       &#10004;     |

# Usage

Example of function call.
```c
#include "esp_aac_enc.h"
#include "esp_adpcm_enc.h"
#include "esp_g711_enc.h"
#include "esp_amrwb_enc.h"
#include "esp_amrnb_enc.h"
#include "esp_opus_enc.h"
#include "esp_pcm_enc.h"
#include "esp_audio_enc.h"
#include "esp_audio_enc_def.h"
#include "esp_audio_def.h"
// This is an example of using encoder interface to encode audio.
void audio_encoder_test(void)
{
    int times = 0;
    FILE *in_file = NULL;
    FILE *out_file = NULL;
    esp_audio_enc_in_frame_t in_frame = { 0 };
    esp_audio_enc_out_frame_t out_frame = { 0 };
    esp_audio_enc_handle_t enc_handle = NULL;
    uint8_t *inbuf = NULL;
    uint8_t *outbuf = NULL;
    esp_audio_err_t ret = ESP_AUDIO_ERR_OK;
    // Register audio encoder
    esp_audio_enc_t audio_encoder_list[] = {
        ESP_AAC_ENC_DEFAULT(),
        ESP_ADPCM_ENC_DEFAULT(),
        ESP_G711A_ENC_DEFAULT(),
        ESP_G711U_ENC_DEFAULT(),
        ESP_AMRNB_ENC_DEFAULT(),
        ESP_AMRWB_ENC_DEFAULT(),
        ESP_OPUS_ENC_DEFAULT(),
        ESP_PCM_ENC_DEFAULT(),
    };
    ret = esp_audio_enc_install(audio_encoder_list, sizeof(audio_encoder_list) / sizeof(esp_audio_enc_t));
    if (ret != ESP_AUDIO_ERR_OK) {
        printf("audio encoder register failed.\n");
        goto audio_encoder_exit;
    }
    // Set configuration
    esp_audio_enc_config_t cfg = {.type = ESP_AUDIO_TYPE_AAC, 
                                  .cfg_sz = sizeof(esp_aac_enc_config_t),};
    esp_aac_enc_config_t config = ESP_AAC_ENC_CONFIG_DEFAULT();
    config.sample_rate = 8000;
    config.channel = 1;
    config.bitrate = 90000;
    config.adts_used = 1;
    cfg.cfg = &config;
    times = 1;
    // Open stream
    // User need to initialize sdcard module before
    in_file = fopen("/sdcard/pcm/thetest16_1.pcm", "rb");
    if (in_file == NULL) {
        printf("in_file open failed\n");
        goto audio_encoder_exit;
    }
    out_file = fopen("/sdcard/out_music/test.aac", "w+");
    if (out_file == NULL) {
        printf("out_file open failed\n");
        goto audio_encoder_exit;
    }
    // Create encoder handle.
    // To encode two different streams, create two encoder handles to encode audio.
    ret = esp_audio_enc_open(&cfg, &enc_handle);
    if (ret != ESP_AUDIO_ERR_OK) {
        printf("audio encoder open failed.\n");
        goto audio_encoder_exit;
    }
    // Get in/out buffer size
    int in_frame_size = 0;
    int out_frame_size = 0;
    ret = esp_audio_enc_get_frame_size(enc_handle, &in_frame_size, &out_frame_size);
    if (ret != ESP_AUDIO_ERR_OK) {
        printf("audio encoder get frame size failed.\n");
        goto audio_encoder_exit;
    }
    // Malloc in/out buffer
    in_frame_size *= times;
    out_frame_size *= times;
    inbuf = calloc(1, in_frame_size);
    if (!inbuf) {
        printf("inbuf malloc failed.\n");
        goto audio_encoder_exit;
    }
    outbuf = calloc(1, out_frame_size);
    if (!outbuf) {
        printf("outbuf malloc failed.\n");
        goto audio_encoder_exit;
    }
    in_frame.buffer = inbuf;
    in_frame.len = in_frame_size;
    out_frame.buffer = outbuf;
    out_frame.len = out_frame_size;
    // Encode process
    int in_read = 0;
    while ((in_read = fread(inbuf, 1, in_frame_size, in_file)) > 0) {
        if (in_read < in_frame_size) {
            memset(inbuf + in_read, 0, in_frame_size - in_read);
        }
        ret = esp_audio_enc_process(enc_handle, &in_frame, &out_frame);
        if (ret != ESP_AUDIO_ERR_OK) {
            printf("audio encoder process failed.\n");
            goto audio_encoder_exit;
        }
        fwrite(outbuf, 1, out_frame.encoded_bytes, out_file);
    }
audio_encoder_exit:
    if (in_file) {
        fclose(in_file);
    }
    if (out_file) {
        fclose(out_file);
    }
    if (inbuf) {
        free(inbuf);
    }
    if (outbuf) {
        free(outbuf);
    }
    if (enc_handle) {
        esp_audio_enc_close(enc_handle);
    }
    esp_audio_enc_uninstall();
    return;
}
```

```c
#include "esp_aac_enc.h"
#include "esp_audio_enc_def.h"
#include "esp_audio_def.h"
// This is an example of using a simple encoder interface to encode audio.
void aac_encoder_test(void)
{
    esp_audio_err_t ret;
    void *enc_handle = NULL;
    FILE *in_file = NULL;
    FILE *out_file = NULL;
    uint8_t *inbuf = NULL;
    uint8_t *outbuf = NULL;
    int in_read = 0;
    int in_frame_size = 0;
    int out_frame_size = 0;
    int times = 0;
    // Open stream
    // User need to initialize sdcard module before
    in_file = fopen("/sdcard/pcm/thetest8_1.pcm", "rb");
    if (in_file == NULL) {
        printf("in_file open failed\n");
        goto audio_encoder_exit;
    }
    out_file = fopen("/sdcard/out_music/thetest1.aac", "w+");
    if (out_file == NULL) {
        printf("out_file open failed\n");
        goto audio_encoder_exit;
    }
    // Set configuration
    esp_aac_enc_config_t config = ESP_AAC_ENC_CONFIG_DEFAULT();
    config.sample_rate = 8000;
    config.channel = 1;
    config.bitrate = 90000;
    config.adts_used = 1;
    // Create encoder handle
    ret = esp_aac_enc_open(&config, sizeof(esp_aac_enc_config_t), &enc_handle);
    if (ret != 0) {
        printf("Fail to create encoder handle.");
        goto audio_encoder_exit;
    }
    // Get in/out buffer size and malloc in/out buffer
    ret = esp_aac_enc_get_frame_size(enc_handle, &in_frame_size, &out_frame_size);
    times = 4;
    in_frame_size *= times;
    out_frame_size *= times;
    inbuf = calloc(1, in_frame_size);
    if (inbuf == NULL) {
        printf("inbuf malloc failed.\n");
        goto audio_encoder_exit;
    }
    outbuf = calloc(1, out_frame_size);
    if (outbuf == NULL) {
        printf("outbuf malloc failed.\n");
        goto audio_encoder_exit;
    }
    // Encode process
    esp_audio_enc_in_frame_t in_frame = { 0 };
    esp_audio_enc_out_frame_t out_frame = { 0 };
    in_frame.buffer = inbuf;
    in_frame.len = in_frame_size;
    out_frame.buffer = outbuf;
    out_frame.len = out_frame_size;
    while ((in_read = fread(inbuf, 1, in_frame_size, in_file)) > 0) {
        if (in_read < in_frame_size) {
            memset(inbuf + in_read, 0, in_frame_size - in_read);
        }
        ret = esp_aac_enc_process(enc_handle, &in_frame, &out_frame);
        if (ret != ESP_AUDIO_ERR_OK) {
            printf("audio encoder process failed.\n");
            goto audio_encoder_exit;
        }
        fwrite(outbuf, 1, out_frame.encoded_bytes, out_file);
    }
audio_encoder_exit:
    if (in_file) {
        fclose(in_file);
    }
    if (out_file) {
        fclose(out_file);
    }
    if (inbuf) {
        free(inbuf);
    }
    if (outbuf) {
        free(outbuf);
    }
    if (enc_handle) {
        esp_aac_enc_close(enc_handle);
    }
    return;
}
```
# Change log

## Version 1.0.0
- Added ESP Audio Encoder
