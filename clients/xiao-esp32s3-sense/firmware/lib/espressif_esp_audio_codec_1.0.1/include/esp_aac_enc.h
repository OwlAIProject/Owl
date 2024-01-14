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

#ifndef ESP_AAC_ENC_H
#define ESP_AAC_ENC_H

#include <stdbool.h>
#include "esp_audio_enc_def.h"

#ifdef __cplusplus
extern "C" {
#endif

/**
 * @brief      AAC Encoder configurations
 */
typedef struct {
    int sample_rate;    /*!< Support sample rate(Hz) : 96000, 88200, 64000, 48000,
                             44100, 32000, 24000, 22050, 16000, 12000, 11025, 8000 */
    int channel;        /*!< Support channel : mono, dual */
    int bit_per_sample; /*!< Support bit per sample : 16 bit */
    int bitrate;        /*!< Support bitrate(bps) range on mono stream :
                             |samplerate(Hz)|bitrate range(Kbps)|
                             |    8000      |    12 - 48        |
                             |    11025     |    18 - 66        |
                             |    12000     |    20 - 72        |
                             |    16000     |    22 - 96        |
                             |    22050     |    25 - 132       |
                             |    24000     |    31 - 144       |
                             |    32000     |    33 - 160       |
                             |    44100     |    57 - 160       |
                             |    48000     |    59 - 160       |
                             |    64000     |    65 - 160       |
                             |    88200     |    67 - 160       |
                             |    96000     |    70 - 160       | 
                             Note : 1) This table shows the bitrate range corresponding to each samplerate.
                                    2) The bitrate range of dual stream is twice that of mono. */
    bool adts_used;     /*!< Whether write ADTS header, true means add ADTS header, false means raw aac data. */
} esp_aac_enc_config_t;

#define ESP_AAC_ENC_CONFIG_DEFAULT() {             \
    .sample_rate    = ESP_AUDIO_SAMPLE_RATE_44K,   \
    .channel        = ESP_AUDIO_DUAL,              \
    .bit_per_sample = ESP_AUDIO_BIT16,             \
    .bitrate        = 90000,                       \
    .adts_used      = true,                        \
}

#define ESP_AAC_ENC_DEFAULT() {                    \
    .enc_type       = ESP_AUDIO_TYPE_AAC,          \
    .open           = esp_aac_enc_open,            \
    .get_info       = esp_aac_enc_get_info,        \
    .get_frame_size = esp_aac_enc_get_frame_size,  \
    .process        = esp_aac_enc_process,         \
    .close          = esp_aac_enc_close,           \
}

/**
 * @brief       Create AAC encoder handle through encoder configuration.
 * 
 * @param[in]   cfg      AAC encoder configuration.
 * @param[in]   cfg_sz   Size of "esp_aac_enc_config_t".
 * @param[out]  enc_hd   The AAC encoder handle. If AAC encoder handle allocation failed, will be set to NULL.
 * 
 * @return
 *       - ESP_AUDIO_ERR_OK: On success
 *       - ESP_AUDIO_ERR_FAIL: Encoder initialize failed
 *       - ESP_AUDIO_ERR_MEM_LACK: Fail to allocate memory
 *       - ESP_AUDIO_ERR_INVALID_PARAMETER: Invalid parameter
 */
esp_audio_err_t esp_aac_enc_open(void *cfg, uint32_t cfg_sz, void **enc_hd);

/**
 * @brief       Get the input PCM data length and recommended output buffer length needed by encoding one frame. 
 * 
 * @param[in]   enc_hd     The AAC encoder handle.
 * @param[out]  in_size    The input frame size.
 * @param[out]  out_size   The output frame size.
 * 
 * @return
 *       - ESP_AUDIO_ERR_OK: On success
 *       - ESP_AUDIO_ERR_INVALID_PARAMETER: Invalid parameter
 */
esp_audio_err_t esp_aac_enc_get_frame_size(void *enc_hd, int *in_size, int *out_size);

/**
 * @brief     Encode one or multi AAC frame which the frame num is depended on input data length.
 * 
 * @param[in]      enc_hd      The AAC encoder handle.
 * @param[in]      in_frame    Pointer to input data frame.
 * @param[in/out]  out_frame   Pointer to output data frame.
 * 
 * @return
 *       - ESP_AUDIO_ERR_OK: On success
 *       - ESP_AUDIO_ERR_FAIL: Encode error
 *       - ESP_AUDIO_ERR_INVALID_PARAMETER: Invalid parameter
 */
esp_audio_err_t esp_aac_enc_process(void *enc_hd, esp_audio_enc_in_frame_t *in_frame, esp_audio_enc_out_frame_t *out_frame);

/**
 * @brief      Get AAC encoder information from encoder handle.
 * 
 * @param[in]  enc_hd       The AAC encoder handle.
 * @param[in]  enc_info     The AAC encoder information.
 * 
 * @return
 *       - ESP_AUDIO_ERR_OK: On success
 *       - ESP_AUDIO_ERR_INVALID_PARAMETER: Invalid parameter
 */
esp_audio_err_t esp_aac_enc_get_info(void *enc_hd, esp_audio_enc_info_t *enc_info);

/**
 * @brief      Deinitialize AAC encoder handle.
 * 
 * @param[in]  enc_hd    The AAC encoder handle.
 */
void esp_aac_enc_close(void *enc_hd);

#ifdef __cplusplus
}
#endif

#endif
