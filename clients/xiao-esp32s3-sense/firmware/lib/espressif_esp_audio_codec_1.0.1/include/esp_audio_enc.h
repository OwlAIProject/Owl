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

#ifndef ESP_AUDIO_ENC_H
#define ESP_AUDIO_ENC_H

#include "esp_audio_enc_def.h"

#ifdef __cplusplus
extern "C" {
#endif

/**
 * @brief     Handle for audio encoder instance.
 */
typedef void *esp_audio_enc_handle_t;

/**
 * @brief      The structure of encoder library.
 */
typedef struct {
    esp_audio_type_t enc_type;                                                     /*!< Type of audio encoder. */
    esp_audio_err_t (*open)(void *cfg, uint32_t cfg_sz, void **enc_hd);            /*!< Create an encoder handle which 
                                                                                        according to user configuration. */
    esp_audio_err_t (*get_info)(void *enc_hd, esp_audio_enc_info_t *enc_info);     /*!< Get encoder information. */
    esp_audio_err_t (*get_frame_size)(void *enc_hd, int *in_size, int *out_size);  /*!< Get in buffer and out buffer size. */
    esp_audio_err_t (*process)(void *enc_hd, esp_audio_enc_in_frame_t *in_frame, 
                               esp_audio_enc_out_frame_t *out_frame);              /*!< Encode pcm data. */
    void            (*close)(void *enc_hd);                                        /*!< Close an encoder handle. */
} esp_audio_enc_t;

/**
 * @brief      Register encoder library. 
 *             Eg: If user want to add AAC and ADPCM encoder, user can create an array of esp_audio_enc_t,
 *                 then insert 'ESP_AAC_ENC_DEFAULT' and 'ESP_ADPCM_ENC_DEFAULT into it.
 *
 * @param[in]  list      The audio encoder formats list.
 * @param[in]  list_num  The number of audio encoder formats.
 *
 * @return
 *       - ESP_AUDIO_ERR_OK: On success
 *       - ESP_AUDIO_ERR_MEM_LACK: Fail to allocate memory
 *       - ESP_AUDIO_ERR_ALREADY_EXIST: The encoder library is already exist, user must use 'esp_audio_enc_uninstall' to uninstall first
 *       - ESP_AUDIO_ERR_INVALID_PARAMETER: Invalid parameter
 */
esp_audio_err_t esp_audio_enc_install(esp_audio_enc_t *list, uint32_t list_num);

/**
 * @brief       Create encoder handle through encoder configuration.
 *
 * @param[in]   config   Audio encoder configuration. 
 * @param[out]  enc_hd   The encoder handle. If encoder handle allocation failed, will be set to NULL.
 *
 * @return
 *       - ESP_AUDIO_ERR_OK: On success
 *       - ESP_AUDIO_ERR_FAIL: Encoder initialize failed
 *       - ESP_AUDIO_ERR_MEM_LACK: Fail to allocate memory
 *       - ESP_AUDIO_ERR_INVALID_PARAMETER: Invalid parameter
 */
esp_audio_err_t esp_audio_enc_open(esp_audio_enc_config_t *config, esp_audio_enc_handle_t *enc_hd);

/**
 * @brief      Get audio encoder information from encoder handle.
 *
 * @param[in]  enc_hd       The encoder handle.
 * @param[in]  stream_info  The encoder information.
 *
 * @return
 *       - ESP_AUDIO_ERR_OK: On success
 *       - ESP_AUDIO_ERR_INVALID_PARAMETER: Invalid parameter
 */
esp_audio_err_t esp_audio_enc_get_info(esp_audio_enc_handle_t enc_hd, esp_audio_enc_info_t *enc_info);

/**
 * @brief        Get the input PCM data length and recommended output buffer length needed by encoding one frame.
 * 
 * @note         As for PCM and G711 encoder, the 'in_size' and 'out_size' is one sample size. 
 * 
 * @param[in]    enc_hd     The audio encoder handle.
 * @param[out]   in_size    The input frame size. 
 * @param[out]   out_size   The output frame size.
 * 
 * @return
 *       - ESP_AUDIO_ERR_OK: On success
 *       - ESP_AUDIO_ERR_INVALID_PARAMETER: Invalid parameter
 */
esp_audio_err_t esp_audio_enc_get_frame_size(esp_audio_enc_handle_t enc_hd, int *in_size, int *out_size);

/**
 * @brief          Encode one or multi audio frame which the frame num is depended on input data length.
 * 
 * @param[in]      enc_hd     The audio encoder handle.
 * @param[in]      in_frame   Pointer to input data frame.
 * @param[in/out]  out_frame  Pointer to output data frame.
 * 
 * @return
 *       - ESP_AUDIO_ERR_OK: On success
 *       - ESP_AUDIO_ERR_FAIL: Encode error
 *       - ESP_AUDIO_ERR_INVALID_PARAMETER: Invalid parameter
 */
esp_audio_err_t esp_audio_enc_process(esp_audio_enc_handle_t enc_hd, esp_audio_enc_in_frame_t *in_frame, esp_audio_enc_out_frame_t *out_frame);

/**
 * @brief      Close an encoder handle.
 *
 * @param[in]  enc_hd   The encoder handle.
 */
void esp_audio_enc_close(esp_audio_enc_handle_t enc_hd);

/**
 * @brief      Uninstall the inserted encoder libraries by esp_audio_enc_install.
 */
void esp_audio_enc_uninstall(void);

#ifdef __cplusplus
}
#endif

#endif