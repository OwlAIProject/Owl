//
//  Location.swift
//  Owl
//
//  Created by ethan on 1/25/24.
//

import Foundation
import MapKit

struct Location: Codable, Identifiable {
    var id: Int?
    var latitude: Double
    var longitude: Double
    var address: String?
    var captureUUID: String?

    init(id: Int? = nil, latitude: Double, longitude: Double, address: String? = nil, captureUUID: String? = nil) {
        self.id = id
        self.latitude = latitude
        self.longitude = longitude
        self.address = address
        self.captureUUID = captureUUID
    }
    
    enum CodingKeys: String, CodingKey {
        case id
        case latitude
        case longitude
        case address
        case captureUUID = "capture_uuid"
    }
    
    var coordinate: CLLocationCoordinate2D {
        CLLocationCoordinate2D(latitude: latitude, longitude: longitude)
    }
}
