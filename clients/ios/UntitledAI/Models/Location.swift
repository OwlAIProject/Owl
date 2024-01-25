//
//  Location.swift
//  UntitledAI
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

    init(id: Int? = nil, latitude: Double, longitude: Double, address: String? = nil) {
        self.id = id
        self.latitude = latitude
        self.longitude = longitude
        self.address = address
    }

    var coordinate: CLLocationCoordinate2D {
        CLLocationCoordinate2D(latitude: latitude, longitude: longitude)
    }
}
