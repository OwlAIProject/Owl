/*
 * ESPRESSIF MIT License
 *
 * Copyright (c) 2023-2026 <ESPRESSIF SYSTEMS (SHANGHAI) CO., LTD>
 *
 * Permission is hereby granted for use on all ESPRESSIF SYSTEMS products, in which case,
 * it is free of charge, to any person obtaining a copy of this software and associated
 * documentation files (the "Software"), to deal in the Software without restriction, including
 * without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense,
 * and/or sell copies of the Software, and to permit persons to whom the Software is furnished
 * to do so, subject to the following conditions:
 *
 * The above copyright notice and this permission notice shall be included in all copies or
 * substantial portions of the Software.
 *
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
 * IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS
 * FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR
 * COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER
 * IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
 * CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
 *
 */

#ifndef ESP_OPUS_ENC_H
#define ESP_OPUS_ENC_H

#include <stdbool.h>
#include "esp_audio_enc_def.h"

#ifdef __cplusplus
extern "C" {
#endif

/**
 * @brief      Enum of OPUS Encoder frame duration choose.
 */
typedef enum {
    ESP_OPUS_ENC_FRAME_DURATION_ARG    = -1,    /*!< Invalid mode */
    ESP_OPUS_ENC_FRAME_DURATION_2_5_MS = 0,     /*!< Use 2.5 ms frames */
    ESP_OPUS_ENC_FRAME_DURATION_5_MS   = 1,     /*!< Use 5 ms frames */
    ESP_OPUS_ENC_FRAME_DURATION_10_MS  = 2,     /*!< Use 10 ms frames */
    ESP_OPUS_ENC_FRAME_DURATION_20_MS  = 3,     /*!< Use 20 ms frames */
    ESP_OPUS_ENC_FRAME_DURATION_40_MS  = 4,     /*!< Use 40 ms frames */
    ESP_OPUS_ENC_FRAME_DURATION_60_MS  = 5,     /*!< Use 60 ms frames */
} esp_opus_enc_frame_duration_t;

/**
 * @brief      Enum of OPUS Encoder application choose.
 */
typedef enum {
    ESP_OPUS_ENC_APPLICATION_ARG      = -1,      /*!< Invalid mode */
    ESP_OPUS_ENC_APPLICATION_VOIP     = 0,       /*!< Voip mode which is best for most VoIP/videoconference applications 
                                                      where listening quality and intelligibility matter most. */  
    ESP_OPUS_ENC_APPLICATION_AUDIO    = 1,       /*!< Audio mode which is best for broadcast/high-fidelity application 
                                                      where the decoded audio should be as close as possible to the input. */
    ESP_OPUS_ENC_APPLICATION_LOWDELAY = 2,       /*!< LOWDELAY mode is only use when lowest-achievable latency is what matters most. */
} esp_opus_enc_application_t;

/**
 * @brief      OPUS Encoder configurations
 */
typedef struct {
    int                           sample_rate;        /*!< The sample rate of OPUS audio.
                                                           This must be one of 8000, 12000,
                                                           16000, 24000, or 48000. */
    int                           channel;            /*!< The numble of channels of OPUS audio.
                                                           This must be mono or dual. */
    int                           bit_per_sample;     /*!< The bit per sample of OPUS audio.
                                                           This must be 16 */
    int                           bitrate;            /*!< Suggest bitrate(Kbps) range on mono stream :
                                                           | frame_duration(ms)|    2.5    |     5     |    10    |    20    |    40    |    60    | 
                                                           |   samplerate(Hz)  |           |           |          |          |          |          |
                                                           |       8000        | 50 - 128  | 40 - 128  | 20 - 128 | 20 - 128 | 20 - 128 | 20 - 128 |
                                                           |       12000       | 60 - 192  | 50 - 192  | 30 - 192 | 20 - 192 | 20 - 192 | 20 - 192 |
                                                           |       16000       | 70 - 256  | 60 - 256  | 50 - 256 | 20 - 256 | 20 - 256 | 20 - 256 |
                                                           |       24000       | 70 - 384  | 60 - 384  | 60 - 384 | 60 - 384 | 50 - 384 | 60 - 384 |
                                                           |       48000       | 80 - 510  | 80 - 510  | 80 - 510 | 70 - 510 | 70 - 510 | 70 - 510 |
                                                           Note : 1) This table shows the bitrate range corresponding to each samplerate and frame duration.
                                                                  2) The bitrate range of dual stream is the same that of mono. */
    esp_opus_enc_frame_duration_t frame_duration;     /*!< The duration of one frame.
                                                           This must be 2.5, 5, 10, 20, 40 or 60 ms. */
    esp_opus_enc_application_t    application_mode;   /*!< The application mode. */
    int                           complexity;         /*!< Indicates the complexity of OPUS encoding. 0 is lowest. 10 is higest.*/
    bool                          enable_fec;         /*!< Configures the encoder's use of inband forward error correction (FEC) */
    bool                          enable_dtx;         /*!< Configures the encoder's use of discontinuous transmission (DTX) */
} esp_opus_enc_config_t;

#define ESP_OPUS_ENC_CONFIG_DEFAULT() {                      \
    .sample_rate        = ESP_AUDIO_SAMPLE_RATE_8K,          \
    .channel            = ESP_AUDIO_DUAL,                    \
    .bit_per_sample     = ESP_AUDIO_BIT16,                   \
    .bitrate            = 90000,                             \
    .frame_duration     = ESP_OPUS_ENC_FRAME_DURATION_20_MS, \
    .application_mode   = ESP_OPUS_ENC_APPLICATION_VOIP,     \
    .complexity         = 0,                                 \
    .enable_fec         = false,                             \
    .enable_dtx         = false,                             \
}

#define ESP_OPUS_ENC_DEFAULT() {                   \
    .enc_type       = ESP_AUDIO_TYPE_OPUS,         \
    .open           = esp_opus_enc_open,           \
    .get_info       = esp_opus_enc_get_info,       \
    .get_frame_size = esp_opus_enc_get_frame_size, \
    .process        = esp_opus_enc_process,        \
    .close          = esp_opus_enc_close,          \
}

/**
 * @brief       Create OPUS encoder handle through encoder configuration.
 * 
 * @param[in]   cfg      OPUS encoder configuration.
 * @param[in]   cfg_sz   Size of "esp_opus_enc_config_t".
 * @param[out]  enc_hd   The OPUS encoder handle. If OPUS encoder handle allocation failed, will be set to NULL.
 * 
 * @return
 *       - ESP_AUDIO_ERR_OK: On success
 *       - ESP_AUDIO_ERR_FAIL: Encoder initialize failed
 *       - ESP_AUDIO_ERR_MEM_LACK: Fail to allocate memory
 *       - ESP_AUDIO_ERR_INVALID_PARAMETER: Invalid parameter
 */
esp_audio_err_t esp_opus_enc_open(void *cfg, uint32_t cfg_sz, void **enc_hd);

/**
 * @brief        Get the input PCM data length and recommended output buffer length needed by encoding one frame.
 * 
 * @param[in]    enc_hd     The OPUS encoder handle.
 * @param[out]   in_size    The input frame size.
 * @param[out]   out_size   The output frame size.
 * 
 * @return
 *       - ESP_AUDIO_ERR_OK: On success
 *       - ESP_AUDIO_ERR_INVALID_PARAMETER: Invalid parameter
 */
esp_audio_err_t esp_opus_enc_get_frame_size(void *enc_hd, int *in_size, int *out_size);

/**
 * @brief          Encode one or multi OPUS frame which the frame num is depended on input data length.
 * 
 * @param[in]      enc_hd      The OPUS encoder handle.
 * @param[in]      in_frame    Pointer to input data frame.
 * @param[in/out]  out_frame   Pointer to output data frame.
 * 
 * @return
 *       - ESP_AUDIO_ERR_OK: On success
 *       - ESP_AUDIO_ERR_FAIL: Encode error
 *       - ESP_AUDIO_ERR_INVALID_PARAMETER: Invalid parameter
 */
esp_audio_err_t esp_opus_enc_process(void *enc_hd, esp_audio_enc_in_frame_t *in_frame, esp_audio_enc_out_frame_t *out_frame);

/**
 * @brief      Get OPUS encoder information from encoder handle.
 * 
 * @param[in]  enc_hd      The OPUS encoder handle.
 * @param[in]  enc_info    The OPUS encoder information.
 * 
 * @return
 *       - ESP_AUDIO_ERR_OK: On success
 *       - ESP_AUDIO_ERR_INVALID_PARAMETER: Invalid parameter 
 */
esp_audio_err_t esp_opus_enc_get_info(void *enc_hd, esp_audio_enc_info_t *enc_info);

/**
 * @brief      Deinitialize OPUS encoder handle.
 * 
 * @param[in]  enc_hd    The OPUS encoder handle. 
 */
void esp_opus_enc_close(void *enc_hd);

#ifdef __cplusplus
}
#endif

#endif
