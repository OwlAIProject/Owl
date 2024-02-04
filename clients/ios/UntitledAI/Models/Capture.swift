//
//  Capture.swift
//  UntitledAI
//
//  Created by ethan on 1/26/24.
//

import Foundation

class Capture {
    let captureUUID: String
    let deviceName: String

    init(deviceName: String, captureUUID: String? = nil) {
        self.captureUUID = captureUUID ?? UUID().hex
        self.deviceName = deviceName
    }
}
