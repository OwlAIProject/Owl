package com.owl.Owl

import android.annotation.SuppressLint
import android.content.Context
import android.media.*
import io.socket.client.IO
import io.socket.client.Socket
import java.net.URI
import kotlin.concurrent.thread
import kotlin.experimental.or

class AudioStreamer(private val context: Context, private val captureUUID: String) {

    private var audioRecord: AudioRecord? = null
    private var audioEncoder: MediaCodec? = null
    private var socket: Socket? = null
    private val serverUrl = AppConstants.apiBaseURL
    private val sampleRate = 44100
    private val channelConfig = AudioFormat.CHANNEL_IN_MONO
    private val audioFormat = AudioFormat.ENCODING_PCM_16BIT
    private val bufferSize = AudioRecord.getMinBufferSize(sampleRate, channelConfig, audioFormat)
    private val deviceName = "android"

    @Volatile
    private var isStreaming = false

    init {
        initializeSocket()
    }

    private fun initializeSocket() {
        try {
            val options = IO.Options.builder()
                .setExtraHeaders(mapOf("Authorization" to listOf("Bearer ${AppConstants.clientToken}")))
                .build()
            socket = IO.socket(URI.create(serverUrl), options)
            socket?.connect()
        } catch (e: Exception) {
            e.printStackTrace()
        }
    }

    @android.annotation.SuppressLint("MissingPermission")
    fun startStreaming() {
        setupAudioRecord()
        setupAudioEncoder()

        audioRecord?.startRecording()
        audioEncoder?.start()
        isStreaming = true

        thread(start = true) { captureAndEncodeLoop() }
    }

    @SuppressLint("MissingPermission")
    private fun setupAudioRecord() {
        audioRecord = AudioRecord.Builder()
            .setAudioSource(MediaRecorder.AudioSource.MIC)
            .setAudioFormat(AudioFormat.Builder()
                .setEncoding(audioFormat)
                .setSampleRate(sampleRate)
                .setChannelMask(channelConfig)
                .build())
            .setBufferSizeInBytes(bufferSize)
            .build()
    }

    private fun setupAudioEncoder() {
        val format = MediaFormat.createAudioFormat(MediaFormat.MIMETYPE_AUDIO_AAC, sampleRate, 1)
        format.setInteger(MediaFormat.KEY_AAC_PROFILE, MediaCodecInfo.CodecProfileLevel.AACObjectLC)
        format.setInteger(MediaFormat.KEY_BIT_RATE, 64000)

        audioEncoder = MediaCodec.createEncoderByType(MediaFormat.MIMETYPE_AUDIO_AAC)
        audioEncoder?.configure(format, null, null, MediaCodec.CONFIGURE_FLAG_ENCODE)
    }

    private fun captureAndEncodeLoop() {
        val inputBuffer = ByteArray(bufferSize)
        val bufferInfo = MediaCodec.BufferInfo()
        while (isStreaming) {
            val readResult = audioRecord?.read(inputBuffer, 0, inputBuffer.size) ?: 0
            if (readResult > 0) {
                encode(inputBuffer, readResult, bufferInfo)
            }
        }
        audioEncoder?.signalEndOfInputStream()
        releaseResources()
    }

    private fun encode(input: ByteArray, length: Int, bufferInfo: MediaCodec.BufferInfo) {
        val inputBufferIndex = audioEncoder?.dequeueInputBuffer(10000) ?: -1
        if (inputBufferIndex >= 0) {
            val inputBuffer = audioEncoder?.getInputBuffer(inputBufferIndex)
            inputBuffer?.clear()

            // Don't allow buffer to overflow
            val bytesToEncode = minOf(inputBuffer?.remaining() ?: 0, length)

            inputBuffer?.put(input, 0, bytesToEncode)
            audioEncoder?.queueInputBuffer(inputBufferIndex, 0, bytesToEncode, System.nanoTime() / 1000, 0)
        }

        var outputBufferIndex = audioEncoder?.dequeueOutputBuffer(bufferInfo, 10000) ?: -1
        while (outputBufferIndex >= 0) {
            val outputBuffer = audioEncoder?.getOutputBuffer(outputBufferIndex)
            val outData = ByteArray(bufferInfo.size)
            outputBuffer?.get(outData)
            outputBuffer?.clear()

            // Prepend ADTS header
            val adtsHeader = ByteArray(7)
            addADTSHeader(adtsHeader, bufferInfo.size + adtsHeader.size)

            // Combine ADTS header and encoded AAC frame
            val packet = ByteArray(adtsHeader.size + outData.size)
            System.arraycopy(adtsHeader, 0, packet, 0, adtsHeader.size)
            System.arraycopy(outData, 0, packet, adtsHeader.size, outData.size)

            // Send the packetized data
            socket?.emit("audio_data", packet, deviceName, captureUUID)

            audioEncoder?.releaseOutputBuffer(outputBufferIndex, false)
            outputBufferIndex = audioEncoder?.dequeueOutputBuffer(bufferInfo, 0) ?: -1
        }
    }

    private fun addADTSHeader(packet: ByteArray, packetLen: Int) {
        val profile = 2 // AAC LC
        val freqIdx = 4 // 44.1KHz
        val chanCfg = 1 // Mono

        // fill in ADTS data
        packet[0] = 0xFF.toByte()
        packet[1] = 0xF9.toByte()
        packet[2] = ((profile - 1) shl 6).toByte() or ((freqIdx shl 2).toByte()) or ((chanCfg shr 2).toByte())
        packet[3] = ((chanCfg and 3) shl 6).toByte() or ((packetLen shr 11).toByte())
        packet[4] = ((packetLen and 0x7FF) shr 3).toByte()
        packet[5] = ((packetLen and 7) shl 5).toByte() or 0x1F
        packet[6] = 0xFC.toByte()
    }

    private fun releaseResources() {
        audioRecord?.stop()
        audioRecord?.release()
        audioRecord = null

        audioEncoder?.stop()
        audioEncoder?.release()
        audioEncoder = null

        socket?.disconnect()
    }

    fun stopStreaming() {
        isStreaming = false
    }
}

