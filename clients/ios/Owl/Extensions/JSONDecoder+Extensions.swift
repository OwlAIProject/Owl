//
//  JSONDecoder+Decoding.swift
//  Owl
//
//  Created by ethan on 1/23/24.
//

import Foundation

extension JSONDecoder {
    static func decode<T: Codable>(_ type: T.Type, from jsonString: String) -> Result<T, Error> {
        guard let data = jsonString.data(using: .utf8) else {
            return .failure(DecodingError.dataCorrupted(DecodingError.Context(codingPath: [], debugDescription: "Data conversion failed")))
        }
        
        do {
            let decodedObject = try JSONDecoder().decode(T.self, from: data)
            return .success(decodedObject)
        } catch {
            return .failure(error)
        }
    }
}

extension JSONDecoder {
    static func dateDecoder() -> JSONDecoder {
        let decoder = JSONDecoder()
        // nonsense until we can fix the server to be consistent
        decoder.dateDecodingStrategy = .custom({ (decoder) -> Date in
            let container = try decoder.singleValueContainer()
            let dateString = try container.decode(String.self)
            
            let dateFormatter = DateFormatter()
            dateFormatter.locale = Locale(identifier: "en_US_POSIX")
            dateFormatter.timeZone = TimeZone(secondsFromGMT: 0) // Set timezone to UTC
            
            // Format for UTC dates with 'Z'
            dateFormatter.dateFormat = "yyyy-MM-dd'T'HH:mm:ss.SSSSSSZ"
            if let date = dateFormatter.date(from: dateString) {
                return date
            }
            
            // Format for UTC dates without 'Z'
            dateFormatter.dateFormat = "yyyy-MM-dd'T'HH:mm:ss.SSSSSS"
            if let date = dateFormatter.date(from: dateString) {
                return date
            }
            
            // If neither format works, throw an error
            throw DecodingError.dataCorruptedError(in: container, debugDescription: "Cannot decode date string: \(dateString)")
        })
        
        return decoder
    }
}
