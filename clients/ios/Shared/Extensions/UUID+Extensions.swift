//
//  UUID+Extensions.swift
//  Owl
//
//  Created by Bart Trzynadlowski on 1/24/24.
//

import Foundation

extension UUID {
    /// - Returns: UUID as a string of 32 lowercase hex digits (like Python's .hex attribute).
    var hex: String {
        let (b0, b1, b2, b3, b4, b5, b6, b7, b8, b9, b10, b11, b12, b13, b14, b15) = self.uuid
        return String(
            format: "%02x%02x%02x%02x%02x%02x%02x%02x%02x%02x%02x%02x%02x%02x%02x%02x",
            b0, b1, b2, b3, b4, b5, b6, b7, b8, b9, b10, b11, b12, b13, b14, b15
        )
    }
}
