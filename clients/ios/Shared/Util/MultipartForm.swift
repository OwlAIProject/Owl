//
//  MultipartForm.swift
//  Owl
//
//  Created by Bart Trzynadlowski on 12/19/23.
//

import Foundation

class MultipartForm {
    class Field {
        private let _name: String
        private let _filename: String
        private let _contentType: String
        private let _data: Data
        private let _isFile: Bool

        /// Text field.
        init(name: String, text: String, isJSON: Bool = false) {
            _name = name
            _data = text.data(using: .utf8)!
            _contentType = isJSON ? "application/json" : ""
            _filename = ""
            _isFile = false
        }

        /// Text field, value provided as data.
        init(name: String, data: Data, isJSON: Bool = false) {
            _name = name
            _data = data
            _contentType = isJSON ? "application/json" : ""
            _filename = ""
            _isFile = false
        }

        /// File attachment.
        init(name: String, filename: String, contentType: String, data: Data) {
            _name = name
            _filename = filename
            _contentType = contentType
            _data = data
            _isFile = true
        }

        fileprivate func serialize(boundary: String) -> Data {
            var data = Data()
            data.append("\r\n--\(boundary)\r\n".data(using: .utf8)!)
            if _isFile {
                data.append("Content-Disposition:form-data;name=\"\(_name)\";filename=\"\(_filename)\"\r\n".data(using: .utf8)!)
            } else {
                data.append("Content-Disposition:form-data;name=\"\(_name)\"\r\n".data(using: .utf8)!)
            }
            if _contentType.count > 0 {
                data.append("Content-Type:\(_contentType)\r\n\r\n".data(using: .utf8)!)
            } else {
                data.append("\r\n".data(using: .utf8)!)
            }
            data.append(_data)
            return data
        }
    }

    private let _fields: [Field]
    private let _boundary = UUID().uuidString

    var boundary: String { _boundary }

    init(fields: [Field]) {
        _fields = fields
    }

    func serialize() -> Data {
        var formData = Data()

        // Serialize all fields
        for field in _fields {
            formData.append(field.serialize(boundary: _boundary))
        }

        // Terminate
        formData.append("\r\n--\(boundary)--\r\n".data(using: .utf8)!)

        return formData
    }
}
