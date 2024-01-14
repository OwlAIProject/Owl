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

#ifndef ESP_PCM_ENC_H
#define ESP_PCM_ENC_H

#include "esp_audio_enc_def.h"

#ifdef __cplusplus
extern "C" {
#endif

/**
 * @brief      PCM Encoder configurations
 */
typedef struct {
    int sample_rate;    /*!< The sample rate of audio. */
    int channel;        /*!< The channel num of audio. */
    int bit_per_sample; /*!< The bit per sample of audio */
} esp_pcm_enc_config_t;

#define ESP_PCM_ENC_CONFIG_DEFAULT() {              \
    .sample_rate       = ESP_AUDIO_SAMPLE_RATE_44K, \
    .channel           = ESP_AUDIO_DUAL,            \
    .bit_per_sample    = ESP_AUDIO_BIT16,           \
}

#define ESP_PCM_ENC_DEFAULT() {                   \
    .enc_type       = ESP_AUDIO_TYPE_PCM,         \
    .open           = esp_pcm_enc_open,           \
    .get_info       = esp_pcm_enc_get_info,       \
    .get_frame_size = esp_pcm_enc_get_frame_size, \
    .process        = esp_pcm_enc_process,        \
    .close          = esp_pcm_enc_close,          \
}

/**
 * @brief       Create PCM encoder handle through encoder configuration.
 * 
 * @param[in]   cfg      PCM encoder configuration.
 * @param[in]   cfg_sz   Size of "esp_pcm_enc_config_t".
 * @param[out]  enc_hd   The PCM encoder handle. If PCM encoder handle allocation failed, will be set to NULL.
 * 
 * @return
 *       - ESP_AUDIO_ERR_OK: On success
 *       - ESP_AUDIO_ERR_FAIL: Encoder initialize failed
 *       - ESP_AUDIO_ERR_MEM_LACK: Fail to allocate memory
 *       - ESP_AUDIO_ERR_INVALID_PARAMETER: Invalid parameter
 */
esp_audio_err_t esp_pcm_enc_open(void *cfg, uint32_t cfg_sz, void **enc_hd);

/**
 * @brief      Get the input PCM data length and recommended output buffer length needed by encoding one frame.
 * 
 * @param[in]    enc_hd      The PCM encoder handle.
 * @param[out]   in_size     The input frame size which is one sample size. 
 *                           If user want to encode more samples at once, 
 *                           the input length can be set to several times
 *                           of 'in_size'.
 * @param[out]   out_size    The output frame size which is one sample size.
 *                           If user want to encode more samples at once, 
 *                           the output length can be set to several times
 *                           of 'out_size'.
 * 
 * @return
 *       - ESP_AUDIO_ERR_OK: On success
 *       - ESP_AUDIO_ERR_INVALID_PARAMETER: Invalid parameter
 */
esp_audio_err_t esp_pcm_enc_get_frame_size(void *enc_hd, int *in_size, int *out_size);

/**
 * @brief          Encode one or multi PCM frame which the frame num is depended on input data length.
 * 
 * @param[in]      enc_hd      The PCM encoder handle.
 * @param[in]      in_frame    Pointer to input data frame.
 * @param[in/out]  out_frame   Pointer to output data frame.
 * 
 * @return
 *       - ESP_AUDIO_ERR_OK: On success
 *       - ESP_AUDIO_ERR_INVALID_PARAMETER: Invalid parameter
 */
esp_audio_err_t esp_pcm_enc_process(void *enc_hd, esp_audio_enc_in_frame_t *in_frame, esp_audio_enc_out_frame_t *out_frame);

/**
 * @brief      Get PCM encoder information from encoder handle. 
 * 
 * @param[in]  enc_hd      The PCM encoder handle.
 * @param[in]  enc_info    The PCM encoder information.
 * 
 * @return
 *       - ESP_AUDIO_ERR_OK: On success
 *       - ESP_AUDIO_ERR_INVALID_PARAMETER: Invalid parameter
 */
esp_audio_err_t esp_pcm_enc_get_info(void *enc_hd, esp_audio_enc_info_t *enc_info);

/**
 * @brief      Deinitialize PCM encoder handle.
 * 
 * @param[in]  enc_hd    The PCM encoder handle.
 */
void esp_pcm_enc_close(void *enc_hd);

#ifdef __cplusplus
}
#endif

#endif
