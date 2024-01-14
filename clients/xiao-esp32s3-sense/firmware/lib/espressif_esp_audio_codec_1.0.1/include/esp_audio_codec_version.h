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

#ifndef ESP_AUDIO_VERSION_H
#define ESP_AUDIO_VERSION_H

#ifdef __cplusplus
extern "C" {
#endif

/**
 *  Features:
 *     - Support encoder: AAC-LC, AMR-NB, AMR-WB, ADPCM, G711a, G711u, OPUS, PCM
 *     - Support encoding bit per sample: 16 bit
 *     - Support register encoder for certain audio type
 *     - Support create multiple encoder handles to encode multi-stream
 * 
 *  To be implemented:
 *     - To support decoder process
 * 
 *  Release Notes:
 *     v1.0.0:
 *     - Add AAC-LC, AMR-NB, AMR-WB, ADPCM, G711a, G711u, OPUS, PCM encoding support
 *     - Add a common encoder interface to register encoder for certain audio type
 *     - Support create multiple encoder handles to encode multi-stream
 */

/**
 * @brief         Get audio codec version string
 */
const char *esp_audio_codec_get_version();

#ifdef __cplusplus
}
#endif

#endif