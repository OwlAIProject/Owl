//
//  CaptureManager.swift
//  UntitledAI
//
//  Created by ethan on 1/26/24.
//

import Foundation

class CaptureManager: ObservableObject {
    static let shared = CaptureManager()

    @Published var currentCapture: Capture? {
        didSet {
            if let capture = currentCapture {
                print("Started new capture session with ID: \(capture.captureId) and device: \(capture.deviceName)")
                LocationManager.shared.sendCurrentLocation()
            } else {
                if let capture = oldValue {
                    print("Ending capture session with ID: \(capture.captureId) and device: \(capture.deviceName)")
                    LocationManager.shared.sendCurrentLocation()
                }
            }
        }
    }

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
