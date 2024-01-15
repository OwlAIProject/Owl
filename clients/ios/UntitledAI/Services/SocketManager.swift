//
//  SocketManager.swift
//  UntitledAI
//
//  Created by ethan on 1/15/24.
//

import Foundation
import SocketIO

class SocketManager: ObservableObject {
    static let shared = SocketManager() // Singleton instance

    private let socketManager: SocketIO.SocketManager // Renamed to avoid naming conflict
    private var socket: SocketIOClient!

    private init() {
        socketManager = SocketIO.SocketManager(socketURL: URL(string: AppConstants.apiBaseURL)!, config: [
            .log(false),
            .compress,
            .reconnects(true),
            .reconnectAttempts(-1),
            .reconnectWait(1),
            .reconnectWaitMax(5)
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

    func sendAudioData(_ data: Data) {
        socket.emit("bleData", data)
    }

}
