//
//  SocketManager.swift
//  Owl
//
//  Created by ethan on 1/15/24.
//

import Foundation
import SocketIO

class SocketManager: ObservableObject {
    static let shared = SocketManager() // Singleton instance

    var socket: SocketIOClient!
    
    private let socketManager: SocketIO.SocketManager // Renamed to avoid naming conflict
   
    private init() {
        socketManager = SocketIO.SocketManager(socketURL: URL(string: AppConstants.apiBaseURL)!, config: [
            .log(false),
            .compress,
            .reconnects(true),
            .reconnectAttempts(-1),
            .reconnectWait(1),
            .reconnectWaitMax(5),
            .extraHeaders(["Authorization": "Bearer \(AppConstants.clientToken)"])
        ])
        socket = socketManager.defaultSocket

        socket.on(clientEvent: .connect) { data, ack in
            print("socket connected")
        }

        connect()
    }

    func connect() {
        if !socket.status.active {
            socket.connect()
        }
    }

    func sendAudioData(_ data: Data, capture: Capture) {
        socket.emit("audio_data", data, capture.deviceName, capture.captureUUID)
    }
    
    func finishAudio(capture: Capture) {
        socket.emit("finish_audio", capture.captureUUID)
    }
    
}
