//
//  CaptureManager.swift
//  UntitledAI Watch App
//
//  Created by ethan on 1/13/24.
//

import Foundation
import AVFoundation

class CaptureManager: NSObject {
    static var shared = CaptureManager()
    private var audioEngine = AVAudioEngine()
  
    func startCapturing() {
        NetworkManager.shared.startStreaming()
        setupAudioSession()
        setupAudioEngine()
        startAudioEngine()
    }

    func stopCapturing() {
        audioEngine.inputNode.removeTap(onBus: 0)
        audioEngine.stop()
        NetworkManager.shared.stopStreaming()
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
 
    private func setupAudioEngine() {  // TODO: down sample and/or compress
        let inputNode = audioEngine.inputNode
        let inputFormat = inputNode.inputFormat(forBus: 0)

        let converterFormat = AVAudioFormat(commonFormat: .pcmFormatInt16, sampleRate: 48000, channels: 1, interleaved: true)

        
        let converterNode = AVAudioMixerNode()
        let sinkNode = AVAudioMixerNode()
        
        audioEngine.attach(converterNode)
        audioEngine.attach(sinkNode)
        
        converterNode.installTap(onBus: 0, bufferSize: 1024, format: converterFormat) { (buffer: AVAudioPCMBuffer!, time: AVAudioTime!) -> Void in
            if let data = self.toNSData(buffer: buffer) {
               NetworkManager.shared.writeData(data)

            }
        }
        audioEngine.connect(inputNode, to: converterNode, format: inputFormat)
        audioEngine.connect(converterNode, to: sinkNode, format: converterFormat)
        audioEngine.prepare()
    }
  
    private func startAudioEngine() {
        do {
            try audioEngine.start()
        } catch {
            print("Audio Engine error: \(error)")
        }
    }

    private func toNSData(buffer: AVAudioPCMBuffer) -> Data? {
        let audioBuffer = buffer.audioBufferList.pointee.mBuffers
        return Data(bytes: audioBuffer.mData!, count: Int(audioBuffer.mDataByteSize))
    }
}

