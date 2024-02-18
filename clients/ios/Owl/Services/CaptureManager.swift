//
//  CaptureManager.swift
//  Owl
//
//  Created by ethan on 1/26/24.
//
import Foundation

class CaptureManager: ObservableObject {
    static let shared = CaptureManager()
    
    @Published var currentCapture: Capture?
    
    @Published var isAwaitingReconnection: Bool = false
    
    private init() {
        self.currentCapture = loadCurrentCaptureFromUserDefaults()
    }
    
    public func createCapture(deviceName: String) -> Capture {
        let newCapture = Capture(deviceName: deviceName)
        self.currentCapture = newCapture
        saveCurrentCaptureToUserDefaults()
        return newCapture
    }
    
    func endCapture() {
        guard let capture = currentCapture else {
            print("No active capture session to end.")
            return
        }
        print("Ending capture session with ID: \(capture.captureUUID) and device: \(capture.deviceName)")
        UserDefaults.standard.removeObject(forKey: "currentCapture")
        SocketManager.shared.finishAudio(capture: capture)
        self.currentCapture = nil
    }
    
    func reportDisconnect() {
        currentCapture?.lastDisconnectTime = Date()
        saveCurrentCaptureToUserDefaults()
        self.isAwaitingReconnection = true
        
        DispatchQueue.main.asyncAfter(deadline: .now() + .seconds(AppConstants.bleReconnectWindowSeconds)) { [weak self] in
            guard let self = self, let capture = self.currentCapture else { return }
            
            // Check if there's been a connect after the last disconnect
            if let lastDisconnectTime = capture.lastDisconnectTime,
               let lastConnectTime = capture.lastConnectTime,
               lastDisconnectTime > lastConnectTime {
                // If no new connect has been reported, end the session
                self.endCapture()
            }
        }
    }
    
    func reportConnect() {
        if let capture = currentCapture {
            capture.lastConnectTime = Date()
            saveCurrentCaptureToUserDefaults()
            self.isAwaitingReconnection = false
        }
    }
    
    private func saveCurrentCaptureToUserDefaults() {
        guard let capture = currentCapture else {
            UserDefaults.standard.removeObject(forKey: "currentCapture")
            return
        }
        if let encodedCapture = try? JSONEncoder().encode(capture) {
            UserDefaults.standard.set(encodedCapture, forKey: "currentCapture")
        }
    }
    
    private func loadCurrentCaptureFromUserDefaults() -> Capture? {
        guard let data = UserDefaults.standard.data(forKey: "currentCapture"),
              let capture = try? JSONDecoder().decode(Capture.self, from: data) else {
            return nil
        }
        return capture
    }
}
