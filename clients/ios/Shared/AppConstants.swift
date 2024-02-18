//
//  AppConstants.swift
//  Owl
//
//  Created by ethan on 1/13/24.
//

import Foundation
struct AppConstants {
    static let apiBaseURL = ""
    static let clientToken = ""
    static let bleServiceUUID = "03d5d5c4-a86c-11ee-9d89-8f2089a49e7e"
    static let bleAudioCharacteristicUUID = "b189a505-a86c-11ee-a5fb-8f2089a49e7e"
    static let batteryLevelCharacteristicUUID = "01a7d889-b8cf-4bd6-bc66-169e2c9a1b1e"
    static let chargingStateCharacteristicUUID = "02b7e715-22ad-4b58-9d60-33c5e9b0b9e5"
    static let bleReconnectWindowSeconds = 10
    
    // Feature flags
    static let locationReportingEnabled = true
    static let locationReportingInterval: TimeInterval = 60
}
