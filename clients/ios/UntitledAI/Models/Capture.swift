//
//  Capture.swift
//  UntitledAI
//
//  Created by ethan on 1/26/24.
//

import Foundation

class Capture {
    let captureId: String
    let deviceName: String

    init(deviceName: String, captureId: String? = nil) {
        self.captureId = captureId ?? UUID().uuidString
        self.deviceName = deviceName
    }
}
