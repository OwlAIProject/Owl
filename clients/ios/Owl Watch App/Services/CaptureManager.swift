//
//  CaptureManager.swift
//  Owl Watch App
//
//  Created by ethan on 1/13/24.
//

import Foundation
import AVFoundation

class CaptureManager: NSObject {
    static var shared = CaptureManager()
    
    private var _audioEngine = AVAudioEngine()
    private var _silenceInputMixerNode = AVAudioMixerNode()
    private var _playerNode = AVAudioPlayerNode()
    private let _outputFormat = AVAudioFormat(commonFormat: .pcmFormatInt16, sampleRate: 16000, channels: 1, interleaved: false)!
    private var _converter: AVAudioConverter?

    private var _isStreaming = false
    private var _fileWriter: AudioFileWriter?

    func startCapturing(stream: Bool) {
        _isStreaming = stream
        if _isStreaming {
            NetworkManager.shared.startStreaming()
        } else {
            _fileWriter = AudioFileWriter(fileExtension: "pcm", maxSecondsPerFile: 30)
        }
        setupAudioSession()
        setupAudioGraph()
        startAudioEngine()
    }

    func stopCapturing() {
        _silenceInputMixerNode.removeTap(onBus: 0)
        _audioEngine.stop()
        tearDownAudioGraph()
        if _isStreaming {
            NetworkManager.shared.stopStreaming()
        }
        if let id = _fileWriter?.captureUUID {
            markCaptureComplete(id)
        }
        _fileWriter = nil
        let message = ["event": "stoppedStreaming"]
        WatchConnectivityManager.shared.sendMessage(message)

    }

    private func setupAudioSession() {
        let audioSession = AVAudioSession.sharedInstance()
        do {
            try audioSession.setCategory(.playAndRecord, mode: .default, options: [])
            try audioSession.setActive(true, options: .notifyOthersOnDeactivation)
        } catch {
            print("Audio Session error: \(error)")
        }
    }

    private func setupAudioGraph() {
        // Feed input into mixer node that suppresses audio to avoid feedback while recording. For
        // some reason, need to reduce input volume to 0 (which doesn't affect taps on this node,
        // evidently). Output volume has no effect unless changed *after* the node is attached to
        // the engine and then ends up silencing output as well.
        _silenceInputMixerNode.volume = 0
        _audioEngine.attach(_silenceInputMixerNode)

        // Input node -> silencing mixer node
        let inputNode = _audioEngine.inputNode
        let inputFormat = inputNode.outputFormat(forBus: 0)
        _audioEngine.connect(inputNode, to: _silenceInputMixerNode, format: inputFormat)

        // Connect to main mixer node. We can change the number of samples but not the sample rate
        // here.
        let mainMixerNode = _audioEngine.mainMixerNode
        let mixerFormat = AVAudioFormat(commonFormat: .pcmFormatFloat32, sampleRate: inputFormat.sampleRate, channels: 1, interleaved: false)
        _audioEngine.connect(_silenceInputMixerNode, to: mainMixerNode, format: mixerFormat)

        // Create an output node for playback
        _audioEngine.attach(_playerNode)    // output player
        _audioEngine.connect(_playerNode, to: _audioEngine.mainMixerNode, format: mixerFormat)

        // Start audio engine
        _audioEngine.prepare()
    }

    private func tearDownAudioGraph() {
        _audioEngine.disconnectNodeInput(_silenceInputMixerNode)
        _audioEngine.disconnectNodeOutput(_silenceInputMixerNode)
        _audioEngine.disconnectNodeInput(_playerNode)
        _audioEngine.disconnectNodeOutput(_playerNode)
        _audioEngine.disconnectNodeInput(_audioEngine.inputNode)
        _audioEngine.disconnectNodeOutput(_audioEngine.inputNode)
        _audioEngine.disconnectNodeInput(_audioEngine.mainMixerNode)
        _audioEngine.disconnectNodeOutput(_audioEngine.mainMixerNode)
        _audioEngine.detach(_silenceInputMixerNode)
        _audioEngine.detach(_playerNode)
    }
  
    private func startAudioEngine() {
        // Install a tap that down-samples audio to our desired format and writes to file
        let format = _silenceInputMixerNode.outputFormat(forBus: 0)
        _silenceInputMixerNode.installTap(onBus: 0, bufferSize: 4096, format: format) { [weak self] (buffer: AVAudioPCMBuffer, time: AVAudioTime) in
            guard let self = self else { return }

            // Lazy instantiate converter
            if _converter == nil {
                _converter = AVAudioConverter(from: buffer.format, to: _outputFormat)
                if _converter == nil {
                    print("Error: Unable to create audio converter!")
                }
            }
            guard let converter = _converter else {
                return
            }

            // Allocate buffer for audio
            guard let outputAudioBuffer = AVAudioPCMBuffer(pcmFormat: _outputFormat, frameCapacity: buffer.frameLength) else {
                print("Error: Unable to allocate output buffer")
                return
            }

            // Perform conversion
            var error: NSError?
            var allSamplesReceived = false
            converter.convert(to: outputAudioBuffer, error: &error, withInputFrom: { (inNumPackets: AVAudioPacketCount, outError: UnsafeMutablePointer<AVAudioConverterInputStatus>) -> AVAudioBuffer? in
                // This is the input block that is called repeatedly over and over until the destination is filled
                // to capacity. But that isn't the behavior we want! We want to stop after we have converted the
                // complete input and do not want it to repeat. Hence, we have to do some ridiculous trickery to
                // stop it because whoever designed this API is a maniac. For more details see:
                // https://www.appsloveworld.com/swift/100/27/avaudioconverter-with-avaudioconverterinputblock-stutters-audio-after-processing

                if allSamplesReceived {
                    outError.pointee = .noDataNow
                    return nil
                }
                allSamplesReceived = true
                outError.pointee = .haveData
                return buffer
            })
            guard error == nil else {
                print("Error: Unable to convert audio: \(error!.localizedDescription)")
                return
            }

            // Write
            if _isStreaming {
                if let data = toData(buffer: outputAudioBuffer) {
                    NetworkManager.shared.writeData(data)
                }
            } else {
                _fileWriter?.append(outputAudioBuffer)
            }
        }

        // Start recording
        do {
            try _audioEngine.start()
        } catch {
            print("Audio Engine error: \(error)")
        }
    }

    private func toData(buffer: AVAudioPCMBuffer) -> Data? {
        let audioBuffer = buffer.audioBufferList.pointee.mBuffers
        return Data(bytes: audioBuffer.mData!, count: Int(audioBuffer.mDataByteSize))
    }
}

