//
//  URLRequest+Extensions.swift
//  Owl
//
//  Created by ethan on 2/3/24.
//

import Foundation

extension URLRequest {
    mutating func addCommonHeaders() {
        self.addValue("Bearer \(AppConstants.clientToken)", forHTTPHeaderField: "Authorization")
    }
}
