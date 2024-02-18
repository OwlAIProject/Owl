//
//  WatchConnectivityManager.swift
//  Owl
//
//  Created by ethan on 1/27/24.
//

import Foundation
import WatchConnectivity

class WatchConnectivityManager: NSObject, WCSessionDelegate {

    static let shared = WatchConnectivityManager()
    private var session: WCSession?

    override init() {
        super.init()
        if WCSession.isSupported() {
            session = WCSession.default
            session?.delegate = self
            session?.activate()
        }
    }

    func sendMessage(_ message: [String: Any], replyHandler: (([String: Any]) -> Void)? = nil, errorHandler: ((Error) -> Void)? = nil) {
        if let validSession = session, validSession.isReachable {
            validSession.sendMessage(message, replyHandler: replyHandler, errorHandler: errorHandler)
        } else {
            errorHandler?(NSError(domain: "com.owl.Owl", code: -1, userInfo: [NSLocalizedDescriptionKey: "WatchConnectivity session not reachable"]))
        }
    }

    // WCSessionDelegate methods
    func session(_ session: WCSession, activationDidCompleteWith activationState: WCSessionActivationState, error: Error?) {
        
    }

    func session(_ session: WCSession, didReceiveMessage message: [String : Any]) {
        print(message)
        if let event = message["event"] as? String {
            if event == "startedStreaming", let captureUUID = message["captureUUID"] as? String {
                DispatchQueue.main.async {
                    CaptureManager.shared.currentCapture = Capture(deviceName: "apple_watch", captureUUID: captureUUID)
                }
            } else if event == "stoppedStreaming" {
                DispatchQueue.main.async {
                    CaptureManager.shared.currentCapture = nil
                }
            }
        }
    }

    func sessionDidBecomeInactive(_ session: WCSession) {
        
    }
    
    func sessionDidDeactivate(_ session: WCSession) {
        
    }
    
}
