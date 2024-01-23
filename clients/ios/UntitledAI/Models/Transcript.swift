//
//  Transcript.swift
//  UntitledAI
//
//  Created by ethan on 1/23/24.
//

import Foundation

struct Transcription: Codable {
    var id: Int
    var model: String
    var fileName: String
    var duration: Double
    var sourceDevice: String
    var transcriptionTime: Double
    var utterances: [Utterance]

    enum CodingKeys: String, CodingKey {
        case id, model, duration, utterances
        case fileName = "file_name"
        case sourceDevice = "source_device"
        case transcriptionTime = "transcription_time"
    }
}

struct Utterance: Codable {
    var id: Int
    var start: Double?
    var end: Double?
    var text: String?
    var speaker: String?
    var words: [Word]
}

struct Word: Codable {
    var id: Int
    var word: String
    var start: Double?
    var end: Double?
    var score: Double?
    var speaker: String?
    var utteranceId: Int?

    enum CodingKeys: String, CodingKey {
        case id, word, start, end, score, speaker
        case utteranceId = "utterance_id"
    }
}
