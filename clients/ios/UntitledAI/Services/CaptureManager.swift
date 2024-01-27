//
//  CaptureManager.swift
//  UntitledAI
//
//  Created by ethan on 1/26/24.
//

import Foundation

class CaptureManager {
    static let shared = CaptureManager()

    private var currentCapture: Capture?

    private init() {}

    func createCapture(capture: Capture) {
        currentCapture = capture
        print("Started new capture session with ID: \(capture.captureUUID) and device: \(capture.deviceName)")
    }

    func endCapture() {
        guard let capture = currentCapture else {
            print("No active capture session to end.")
            return
        }
        print("Ending capture session with ID: \(capture.captureUUID) and device: \(capture.deviceName)")
        currentCapture = nil
    }

    func getCurrentCapture() -> Capture? {
        return currentCapture
    }
}
