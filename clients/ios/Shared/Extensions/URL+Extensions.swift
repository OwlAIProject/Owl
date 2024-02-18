//
//  URL+Extensions.swift
//  Owl
//
//  Created by Bart Trzynadlowski on 1/5/24.
//

import Foundation

extension URL {
    static var documents: URL {
        return FileManager
            .default
            .urls(for: .documentDirectory, in: .userDomainMask)[0]
    }
}
