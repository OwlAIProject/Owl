//
//  Conversation.swift
//  UntitledAI
//
//  Created by ethan on 1/23/24.
//

import Foundation

struct ConversationsResponse: Codable {
    var conversations: [Conversation]
}

struct Conversation: Codable {
    var id: Int
    var startTime: Date
    var summary: String
    var transcriptions: [Transcription]
    var primaryLocation: Location?

    enum CodingKeys: String, CodingKey {
        case id
        case startTime = "start_time"
        case summary
        case transcriptions
        case primaryLocation = "primary_location"
    }
}
