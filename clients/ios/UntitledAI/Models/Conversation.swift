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
    var summary: String
    var transcriptions: [Transcription]
}
