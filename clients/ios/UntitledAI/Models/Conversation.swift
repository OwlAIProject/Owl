//
//  Conversation.swift
//  UntitledAI
//
//  Created by ethan on 1/23/24.
//

import Foundation

struct ConversationsResponse: Codable {
    var conversations: [Conversation]
    var conversationsInProgress: [ConversationProgress]

    enum CodingKeys: String, CodingKey {
        case conversations
        case conversationsInProgress = "conversations_in_progress"
    }
}

struct Conversation: Codable {
    var id: Int
    var startTime: Date
    var summary: String
    var shortSummary: String?
    var transcriptions: [Transcription]
    var primaryLocation: Location?

    enum CodingKeys: String, CodingKey {
        case id
        case startTime = "start_time"
        case summary
        case shortSummary = "short_summary"
        case transcriptions
        case primaryLocation = "primary_location"
    }
}

struct ConversationProgress: Codable {
    var conversationUUID: String
    var inConversation: Bool
    var startTime: Date
    var endTime: Date
    var deviceType: String

    enum CodingKeys: String, CodingKey {
        case conversationUUID = "conversation_uuid"
        case inConversation = "in_conversation"
        case startTime = "start_time"
        case endTime = "end_time"
        case deviceType = "device_type"
    }
}
