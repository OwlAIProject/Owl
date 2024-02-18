//
//  AudioFileWriter.swift
//  Owl
//
//  Created by Bart Trzynadlowski on 1/5/24.
//

import AVFoundation
import Foundation

class AudioFileWriter {
    private let _maxSecondsPerFile: Double
    private let _fileExtension: String
    private var _filenameBase: String?
    private var _captureUUID: String?
    private var _fileNumber = 0
    private var _fileHandle: FileHandle?
    private var _fileURL: URL?
    private var _firstWrittenAt: Double?

    public var filenameBase: String? {
        return _filenameBase
    }

    public var fileExtension: String {
        return _fileExtension
    }

    public var captureUUID: String? {
        return _captureUUID
    }

    /// Initializes an audio file writer (with unique capture UUID). Writers should be used for a
    /// single audio capture session and then destroyed.
    /// - Parameter fileExtension: File extension, which communicates format to server. May be
    /// "pcm" or "aac".
    /// - Parameter maxSecondsPerFile: Maximum number of seconds before closing current file chunk
    /// and creating another one. This is measured in real-time because it is assumed that data is
    /// written as fast as it is captured.
    init(fileExtension: String, maxSecondsPerFile: Int) {
        _fileExtension = fileExtension
        _maxSecondsPerFile = Double(maxSecondsPerFile)
    }

    deinit {
        finishCurrentFile()
    }

    /// - Returns: True if filename in URL conforms to format used by `AudioFileWriter`.
    static func isValid(url: URL) -> Bool {
        let baseFilename = url.deletingPathExtension().lastPathComponent
        let parts = baseFilename.components(separatedBy: "_")
        return parts.count == 4 &&
               parts[0] == "audio" &&
               parts[1].count == 32 &&
               parts[2].count == 19 &&
               Int(parts[3]) != nil
    }

    /// Extracts capture UUID from an audio filename.
    /// - Parameter from: Complete file URL.
    /// - Returns: Capture UUID (32 characters) or `nil` if the format was incorrect.
    static func getCaptureUUID(from url: URL) -> String? {
        let baseFilename = url.deletingPathExtension().lastPathComponent
        let parts = baseFilename.components(separatedBy: "_")
        if parts.count != 4 && parts[1].count != 32 {
            return nil
        }
        return parts[1]
    }

    /// Extracts timestamp from an audio filename.
    /// - Parameter from: Complete file URL.
    /// - Returns: Timestamp (yyyyMMdd-HHmmss.SSS format) or `nil` if incorrectly formatted.
    static func getTimestamp(from url: URL) -> String? {
        let baseFilename = url.deletingPathExtension().lastPathComponent
        let parts = baseFilename.components(separatedBy: "_")
        if parts.count != 4 && parts[2].count != 19 {
            return nil
        }
        return parts[2]
    }

    /// Extracts date from an audio filename.
    /// - Parameter from: Complete file URL.
    /// - Returns: Date (yyyyMMdd) or `nil` if incorrectly formatted.
    static func getDate(from url: URL) -> String? {
        let baseFilename = url.deletingPathExtension().lastPathComponent
        let parts = baseFilename.components(separatedBy: "_")
        guard parts.count == 4, parts[2].count == 19 else {
            return nil
        }

        // Split yyyyMMdd-HHmmss.SSS by '-' and get first part
        let timeParts = parts[2].components(separatedBy: "-")
        guard timeParts.count == 2, timeParts[0].count == 8 else {
            return nil
        }
        return timeParts[0]
    }

    /// Extracts chunk number from an audio filename.
    /// - Parameter from: Complete file URL.
    /// - Returns: Chunk number or `nil` if incorrectly formatted.
    static func getChunkNumber(from url: URL) -> Int? {
        let baseFilename = url.deletingPathExtension().lastPathComponent
        let parts = baseFilename.components(separatedBy: "_")
        if parts.count != 4 && parts[3].count < 1 {
            return nil
        }
        return Int(parts[3])
    }

    /// Append signed 16-bit PCM data. If channel data is any other format, this does nothing.
    func append(_ buffer: AVAudioPCMBuffer) {
        guard let samples = buffer.int16ChannelData else {
            return
        }
        let ptr = UnsafeMutableBufferPointer(start: samples.pointee, count: Int(buffer.frameLength))
        ptr.withMemoryRebound(to: UInt8.self) { bytes -> Void in
            let data = Data(bytes: bytes.baseAddress!, count: bytes.count)
            append(data)
        }
    }

    /// Append raw bytes to file.
    func append(_ data: Data) {
        let now = Date.timeIntervalSinceReferenceDate
        if let firstWrittenAt = _firstWrittenAt {
            if now - firstWrittenAt > _maxSecondsPerFile {
                finishCurrentFile()
                _firstWrittenAt = now
            }
        } else {
            _firstWrittenAt = now
        }

        guard let (fileHandle, _) = getFileHandle() else {
            return
        }

        do {
            try fileHandle.seekToEnd()
            try fileHandle.write(contentsOf: data)
        } catch {
            print("[AudioFileWriter] Error: Writing failed")
        }
    }

    /// Gets the next sequentially incremented filename. Recording start is encoded into each.
    /// Recordings are named `audio_UUID_TIMESTAMP_NUM.EXT`.
    private func getNextFilepath() -> URL {
        if _filenameBase == nil {
            let now = Date()
            let formatter = DateFormatter()
            formatter.dateFormat = "yyyyMMdd-HHmmss.SSS"
            formatter.timeZone = TimeZone(abbreviation: "UTC")
            let timestamp = formatter.string(from: now)
            _captureUUID = UUID().hex
            _filenameBase = "audio_\(_captureUUID!)_\(timestamp)"
            // TODO unify captureID generation for chunks and streaming so this can be centralized
            let message = ["event": "startedStreaming", "captureUUID": _captureUUID ?? ""]
            WatchConnectivityManager.shared.sendMessage(message)
        }

        // Will rename to .EXT when complete
        let nextFile = URL.documents.appendingPathComponent("\(_filenameBase!)_\(_fileNumber).\(_fileExtension)-wip")
        _fileNumber += 1

        return nextFile
    }

    /// Lazy open files to produce sequentially incremented files
    private func getFileHandle() -> (FileHandle, URL)? {
        if let fileHandle = _fileHandle, let fileURL = _fileURL {
            return (fileHandle, fileURL)
        }

        let nextFileURL = getNextFilepath()
        _fileURL = nextFileURL

        if !FileManager.default.createFile(atPath: nextFileURL.path(percentEncoded: true), contents: nil, attributes: nil) {
            print("[AudioFileWriter] Error: Unable to create file: \(nextFileURL)")
            return nil
        }

        do {
            _fileHandle = try FileHandle(forWritingTo: nextFileURL)
            print("[AudioFileWriter] New file: \(nextFileURL)")
        } catch {
            print("[AudioFileWriter] Error: Unable to open file for writing: \(nextFileURL)")
        }

        if let fileHandle = _fileHandle {
            return (fileHandle, nextFileURL)
        }
        return nil
    }

    private func finishCurrentFile() {
        if let fileURL = _fileURL {
            Self.renameToFinal(fileURL, fileExtension: _fileExtension)
        }
        try? _fileHandle?.close()
        _fileHandle = nil
        _fileURL = nil
    }

    private static func renameToFinal(_ url: URL, fileExtension: String) {
        do {
            let newURL = url.deletingPathExtension().appendingPathExtension(fileExtension)
            try FileManager.default.moveItem(at: url, to: newURL)
            print("[AudioFileWriter] Renamed \(url.lastPathComponent) -> \(newURL.lastPathComponent)")
        } catch {
            print("[AudioFileWriter] Error: Failed to rename \(url.lastPathComponent)")
        }
    }
}
