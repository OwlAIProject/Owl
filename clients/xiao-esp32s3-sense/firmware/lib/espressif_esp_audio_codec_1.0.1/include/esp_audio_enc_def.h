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

#ifndef ESP_AUDIO_ENC_DEF_H
#define ESP_AUDIO_ENC_DEF_H

#include <stdint.h>
#include "esp_audio_def.h"

#ifdef __cplusplus
extern "C" {
#endif

/**
 * @brief      Audio encoder infomation
 */
typedef struct {
    uint32_t sample_rate;    /*!< The sample rate of audio. */
    uint8_t  channel;        /*!< The channel number of audio. */
    uint8_t  bit_per_sample; /*!< The bit per sample of audio */
    uint32_t bitrate;        /*!< The bit rate of audio */
} esp_audio_enc_info_t;

/**
 * @brief      Audio encoder input frame structure.
 */
typedef struct {
    uint8_t *buffer; /*!< Input data buffer which user can allocate times of input frame size. */
    uint32_t len;    /*!< It is an input parameter and is one or several times of input frame size
                          which is get from 'esp_xxx_enc_get_frame_size'. */
} esp_audio_enc_in_frame_t;

/**
 * @brief      Audio encoder output frame structure.
 */
typedef struct {
    uint8_t *buffer;        /*!< Output data buffer which user can allocate times of output frame size. */
    uint32_t len;           /*!< It is an input parameter and is one or several times of output frame size
                                 which is get from 'esp_xxx_enc_get_frame_size'. */
    uint32_t encoded_bytes; /*!< It is an output parameter which means encoded data length. */
    uint64_t pts;           /*!< Presentation time stamp(PTS) calculated from accumulated input raw frame unit ms. */
} esp_audio_enc_out_frame_t;

/**
 * @brief    Encoder configuration.
 */
typedef struct {
    esp_audio_type_t type;    /*!< Audio encoder type which from 'esp_audio_type_t'. */
    void            *cfg;     /*!< Audio encoder configuration. For example, if choose AAC encoder, 
                                user need to config 'esp_aac_enc_config_t' and set the pointer
                                of this configuration to 'cfg'. */
    uint32_t         cfg_sz;  /*!< Size of "cfg". For example, if choose AAC encoder, the 'cfg_sz' 
                                is sizeof 'esp_aac_enc_config_t'*/
} esp_audio_enc_config_t;

#ifdef __cplusplus
}
#endif
#endif