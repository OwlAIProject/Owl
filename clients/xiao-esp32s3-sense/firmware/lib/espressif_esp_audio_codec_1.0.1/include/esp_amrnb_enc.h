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

#ifndef ESP_AMRNB_ENC_H
#define ESP_AMRNB_ENC_H

#include <stdbool.h>
#include "esp_audio_enc_def.h"

#ifdef __cplusplus
extern "C" {
#endif

/**
 * @brief      Enum of AMRNB Encoder bitrate choose
 */
typedef enum {
    ESP_AMRNB_ENC_BITRATE_UNKNOW = -1,  /*!< Invalid mode */
    ESP_AMRNB_ENC_BITRATE_MR475  = 0,   /*!< 4.75 Kbps */
    ESP_AMRNB_ENC_BITRATE_MR515  = 1,   /*!< 5.15 Kbps */
    ESP_AMRNB_ENC_BITRATE_MR59   = 2,   /*!< 5.90 Kbps */
    ESP_AMRNB_ENC_BITRATE_MR67   = 3,   /*!< 6.70 Kbps */
    ESP_AMRNB_ENC_BITRATE_MR74   = 4,   /*!< 7.40 Kbps */
    ESP_AMRNB_ENC_BITRATE_MR795  = 5,   /*!< 7.95 Kbps */
    ESP_AMRNB_ENC_BITRATE_MR102  = 6,   /*!< 10.2 Kbps */
    ESP_AMRNB_ENC_BITRATE_MR122  = 7,   /*!< 12.2 Kbps */
} esp_amrnb_enc_bitrate_t;

/**
 * @brief      AMRNB Encoder configurations
 */
typedef struct {
    int                     sample_rate;    /*!< The sample rate of audio. Only supprot 8k */
    int                     channel;        /*!< The channel num of audio. Only support mono. */
    int                     bit_per_sample; /*!< The bit per sample of audio */
    bool                    dtx_enable;     /*!< Use dtx technology or not, true to use */
    esp_amrnb_enc_bitrate_t bitrate_mode;   /*!< AMRNB Encoder bitrate choose */
} esp_amrnb_enc_config_t;

#define ESP_AMRNB_ENC_CONFIG_DEFAULT() {            \
    .sample_rate    = ESP_AUDIO_SAMPLE_RATE_8K,     \
    .channel        = ESP_AUDIO_MONO,               \
    .bit_per_sample = ESP_AUDIO_BIT16,              \
    .dtx_enable     = false,                        \
    .bitrate_mode   = ESP_AMRNB_ENC_BITRATE_MR122,  \
}

#define ESP_AMRNB_ENC_DEFAULT() {                   \
    .enc_type       = ESP_AUDIO_TYPE_AMRNB,         \
    .open           = esp_amrnb_enc_open,           \
    .get_info       = esp_amrnb_enc_get_info,       \
    .get_frame_size = esp_amrnb_enc_get_frame_size, \
    .process        = esp_amrnb_enc_process,        \
    .close          = esp_amrnb_enc_close,          \
}

/**
 * @brief       Create AMRNB encoder handle through encoder configuration.
 * 
 * @param[in]   cfg       AMRNB encoder configuration.
 * @param[in]   cfg_sz    Size of "esp_amrnb_enc_config_t".
 * @param[out]  enc_hd    The AMRNB encoder handle. If AMRNB encoder handle allocation failed, will be set to NULL.
 * 
 * @return
 *       - ESP_AUDIO_ERR_OK: On success
 *       - ESP_AUDIO_ERR_FAIL: Encoder initialize failed
 *       - ESP_AUDIO_ERR_MEM_LACK: Fail to allocate memory
 *       - ESP_AUDIO_ERR_INVALID_PARAMETER: Invalid parameter
 */
esp_audio_err_t esp_amrnb_enc_open(void *cfg, uint32_t cfg_sz, void **enc_hd);

/**
 * @brief        Get the input PCM data length and recommended output buffer length needed by encoding one frame. 
 * 
 * @param[in]    enc_hd      The AMRNB encoder handle.
 * @param[out]   in_size     The input frame size.
 * @param[out]   out_size    The output frame size.
 * 
 * @return
 *       - ESP_AUDIO_ERR_OK: On success
 *       - ESP_AUDIO_ERR_INVALID_PARAMETER: Invalid parameter
 */
esp_audio_err_t esp_amrnb_enc_get_frame_size(void *enc_hd, int *in_size, int *out_size);

/**
 * @brief          Encode one or multi AMRNB frame which the frame num is depended on input data length.
 * 
 * @param[in]      enc_hd      The AMRNB encoder handle.
 * @param[in]      in_frame    Pointer to input data frame.
 * @param[in/out]  out_frame   Pointer to output data frame.
 * 
 * @return
 *       - ESP_AUDIO_ERR_OK: On success
 *       - ESP_AUDIO_ERR_FAIL: Encode error
 *       - ESP_AUDIO_ERR_INVALID_PARAMETER: Invalid parameter
 */
esp_audio_err_t esp_amrnb_enc_process(void *enc_hd, esp_audio_enc_in_frame_t *in_frame, esp_audio_enc_out_frame_t *out_frame);

/**
 * @brief      Get AMRNB encoder information from encoder handle.
 * 
 * @param[in]  enc_hd      The AMRNB encoder handle.
 * @param[in]  enc_info    The AMRNB encoder information.
 * 
 * @return
 *       - ESP_AUDIO_ERR_OK: On success
 *       - ESP_AUDIO_ERR_INVALID_PARAMETER: Invalid parameter
 */
esp_audio_err_t esp_amrnb_enc_get_info(void *enc_hd, esp_audio_enc_info_t *enc_info);

/**
 * @brief      Deinitialize AMRNB encoder handle.
 * 
 * @param[in]  enc_hd    The AMRNB encoder handle.
 */
void esp_amrnb_enc_close(void *enc_hd);

#ifdef __cplusplus
}
#endif

#endif
