//
//  Capture.swift
//  Owl
//
//  Created by ethan on 1/26/24.
//

import Foundation

class Capture: Codable {
    let captureUUID: String
    let deviceName: String
    var lastDisconnectTime: Date?
    var lastConnectTime: Date?
    
    init(deviceName: String, captureUUID: String? = nil) {
        self.captureUUID = captureUUID ?? UUID().hex
        self.deviceName = deviceName
        self.lastDisconnectTime = nil
        self.lastConnectTime = Date() 
    }
}
