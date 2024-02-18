//
//  Transcript.swift
//  Owl
//
//  Created by ethan on 1/23/24.
//

import Foundation

struct CaptureFile: Codable {
    var id: Int
    var filePath: String
    var startTime: String
    var deviceType: String

    enum CodingKeys: String, CodingKey {
        case id
        case filePath = "filepath"
        case startTime = "start_time"
        case deviceType = "device_type"
    }
}


struct CaptureFileSegment: Codable {
    var id: Int
    var filePath: String
    var duration: Double?
    var sourceCapture: CaptureFile

    enum CodingKeys: String, CodingKey {
        case id, duration
        case filePath = "filepath"
        case sourceCapture = "source_capture"
    }
}
struct Transcription: Codable {
    var id: Int
    var model: String
    var realtime: Bool
    var transcriptionTime: Double
    var utterances: [Utterance]
    
    enum CodingKeys: String, CodingKey {
        case id, model, utterances, realtime
        case transcriptionTime = "transcription_time"
    }
}

struct Utterance: Codable {
    var id: Int
    var start: Double?
    var end: Double?
    var text: String?
    var speaker: String?
//    var words: [Word]
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
