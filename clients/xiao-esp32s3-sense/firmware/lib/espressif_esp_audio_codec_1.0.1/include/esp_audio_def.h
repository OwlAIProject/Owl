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

#ifndef ESP_AUDIO_DEF_H
#define ESP_AUDIO_DEF_H

#ifdef __cplusplus
extern "C" {
#endif

#define ESP_AUDIO_SAMPLE_RATE_8K  (8000)
#define ESP_AUDIO_SAMPLE_RATE_11K (11025)
#define ESP_AUDIO_SAMPLE_RATE_12K (12000)
#define ESP_AUDIO_SAMPLE_RATE_16K (16000)
#define ESP_AUDIO_SAMPLE_RATE_22K (22050)
#define ESP_AUDIO_SAMPLE_RATE_24K (24000)
#define ESP_AUDIO_SAMPLE_RATE_32K (32000)
#define ESP_AUDIO_SAMPLE_RATE_44K (44100)
#define ESP_AUDIO_SAMPLE_RATE_48K (48000)
#define ESP_AUDIO_SAMPLE_RATE_64K (64000)
#define ESP_AUDIO_SAMPLE_RATE_88K (88200)
#define ESP_AUDIO_SAMPLE_RATE_96K (96000)

#define ESP_AUDIO_BIT8  (8)
#define ESP_AUDIO_BIT16 (16)
#define ESP_AUDIO_BIT24 (24)
#define ESP_AUDIO_BIT32 (32)

#define ESP_AUDIO_MONO (1)
#define ESP_AUDIO_DUAL (2)

/**
 * @brief     Audio codec type
 */
typedef enum {
    ESP_AUDIO_TYPE_UNSUPPORT,
    ESP_AUDIO_TYPE_AMRNB,
    ESP_AUDIO_TYPE_AMRWB,
    ESP_AUDIO_TYPE_AAC,
    ESP_AUDIO_TYPE_G711A,
    ESP_AUDIO_TYPE_G711U,
    ESP_AUDIO_TYPE_OPUS,
    ESP_AUDIO_TYPE_ADPCM,
    ESP_AUDIO_TYPE_PCM,
    ESP_AUDIO_TYPE_FLAC,
    ESP_AUDIO_TYPE_VORBIS,
    ESP_AUDIO_TYPE_MP3,
    ESP_AUDIO_TYPE_MAX,
} esp_audio_type_t;

/**
 * @brief      Audio codec error type definition
 */
typedef enum {
    ESP_AUDIO_ERR_CONTINUE           =  1,    /*!< Continue */
    ESP_AUDIO_ERR_OK                 =  0,    /*!< Success */
    ESP_AUDIO_ERR_FAIL               = -1,    /*!< Fail */
    ESP_AUDIO_ERR_MEM_LACK           = -2,    /*!< Fail to malloc memory */
    ESP_AUDIO_ERR_DATA_LACK          = -3,    /*!< Data is not enough */
    ESP_AUDIO_ERR_HEADER_PARSE       = -4,    /*!< Parse header happened error. */
    ESP_AUDIO_ERR_INVALID_PARAMETER  = -5,    /*!< Input invalid parameter */
    ESP_AUDIO_ERR_ALREADY_EXIST      = -6,    /*!< Audio library is already exist */
    ESP_AUDIO_ERR_NOT_SUPPORT        = -7,    /*!< Not support type */
} esp_audio_err_t;

#ifdef __cplusplus
}
#endif
#endif
