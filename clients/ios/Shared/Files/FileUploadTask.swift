//
//  FileUploadTask.swift
//  UntitledAI
//
//  Created by Bart Trzynadlowski on 1/5/24.
//
// TODO:
// - Handle _uploadAllowed.
// - Handle case of all files uploaded but process command failed. Need to retain etadata on disk.
//

import Foundation
import os

/// Stores IDs of capture sessions that are complete (no more files will be produced). Once all
/// files have been uploaded, processing will be requested.
private var _completedCaptureSessionIDs: Set<String> = []

private var _uploadAllowed = true

fileprivate let _logger = Logger()

fileprivate func log(_ message: String) {
    _logger.notice("[FileUploadTask] \(message, privacy: .public)")
}

@MainActor
func runFileUploadTask(fileExtension: String) async {
    log("Starting upload task...")
    let contentType = "audio/\(fileExtension)"

    // Delete *.*-wip files that are incomplete
    // TODO: if .pcm-wip, these should actually be just fine provided they contain an even number of bytes
    deleteAllFiles(fileExtension: "\(fileExtension)-wip")

    // Get initial files left over from last session. Mark them all completed because these
    // sessions are definitely over.
    let urls = getAudioFilesAscendingTimeOrder(fileExtension: fileExtension)
    for url in urls {
        guard let sessionID = AudioFileWriter.getSessionID(from: url) else {
            deleteFile(url) // remove files with ill-formatted names
            continue
        }
        markSessionComplete(sessionID)
    }

    while true {
        try? await Task.sleep(for: .seconds(5))

        // Sample current files on disk and session IDs known to be complete
        let completedChunkURLs = getAudioFilesAscendingTimeOrder(fileExtension: fileExtension)
        let allInProgressURLs = completedChunkURLs + getAudioFilesAscendingTimeOrder(fileExtension: "\(fileExtension)-wip")
        let completedCaptureSessionIDs = _completedCaptureSessionIDs

        // Process any completed sessions that have been completely uploaded
        let processed = await tryProcessUploadedSessions(
            existingURLs: allInProgressURLs,
            completedCaptureSessionIDs: completedCaptureSessionIDs
        )
        for sessionID in processed {
            _completedCaptureSessionIDs.remove(sessionID)
        }

        // Upload each. Need to group by session ID because if any chunk fails, we need to skip all
        // subsequent files in session to prevent chunks from being sent out of order. We sorted
        // by time earlier, files will remain in this order.
        var urlsBySessionID: [String: [URL]] = [:]
        for url in completedChunkURLs {
            guard let sessionID = AudioFileWriter.getSessionID(from: url) else {
                deleteFile(url)
                continue
            }
            var urls = urlsBySessionID[sessionID] == nil ? [] : urlsBySessionID[sessionID]!
            urls.append(url)
            urlsBySessionID[sessionID] = urls
        }
        for (_, urls) in urlsBySessionID {
            for url in urls {
                let succeeded = await uploadFile(url, contentType: contentType)
                if succeeded {
                    deleteFile(url)
                } else {
                    // Skip remaining URLs for this session to avoid uploading out of order
                    break
                }
            }
        }
    }
}

func setUploadAllowed(to allowed: Bool) {
    _uploadAllowed = allowed
    if allowed {
        log("Uploading enabled")
    } else {
        log("Uploading disabled")
    }
}

func markSessionComplete(_ sessionID: String) {
    _completedCaptureSessionIDs.insert(sessionID)
    log("Added \(sessionID) to completed queue")
}

fileprivate func tryProcessUploadedSessions(existingURLs urls: [URL], completedCaptureSessionIDs: Set<String>) async -> [String] {
    // Once we have uploaded files that were marked completed, process them
    var sessionIDsToProcess: [String] = []
    for sessionID in completedCaptureSessionIDs {
        let moreToUpload = urls.contains { AudioFileWriter.getSessionID(from: $0) == sessionID }
        if moreToUpload {
            log("Cannot process \(sessionID) yet, there is more to upload")
            continue
        }

        // No matches on the file system, we've finished uploading this file completely. Process!
        log("Ready to process \(sessionID)")
        sessionIDsToProcess.append(sessionID)
    }

    var sessionIDsSuccessfullyProcessed: [String] = []
    for sessionID in sessionIDsToProcess {
        log("Processing \(sessionID)...")
        if await processCapture(sessionID) {
            sessionIDsSuccessfullyProcessed.append(sessionID)
        }
    }

    // Return what was processed
    return sessionIDsSuccessfullyProcessed
}

fileprivate func uploadFile(_ url: URL, contentType: String) async -> Bool {
    guard let fileData = try? Data(contentsOf: url),
          let sessionID = AudioFileWriter.getSessionID(from: url),
          let timestamp = AudioFileWriter.getTimestamp(from: url) else {
        log("Error: Failed to load \(url) from disk")
        return false
    }

    let filename = url.lastPathComponent
    log("Uploading chunk \(filename)...")

    // Create form data
    let fields: [MultipartForm.Field] = [
        .init(name: "file", filename: filename, contentType: contentType, data: fileData),
        .init(name: "session_id", text: sessionID),
        .init(name: "timestamp", text: timestamp),
        .init(name: "device_type", text: "apple_watch")
    ]
    let form = MultipartForm(fields: fields)

    // Request type
    let url = URL(string: "\(AppConstants.apiBaseURL)/capture/upload_chunk")!
    var request = URLRequest(url: url)
    request.httpMethod = "POST"
    request.setValue("multipart/form-data;boundary=\(form.boundary)", forHTTPHeaderField: "Content-Type")

    // Try upload
    do
    {
        let (_, response) = try await URLSession.shared.upload(for: request, from: form.serialize())
        guard let response = response as? HTTPURLResponse,
            (200...299).contains(response.statusCode) else {
            if let response = response as? HTTPURLResponse {
                log("Error: Code \(response.statusCode)")
                return false
            } else {
                log("Error: Unknown error trying to communicate with server")
                return false
            }
        }
        log("Uploaded file successfully")
        return true
    } catch {
        log("Error: Upload failed: \(error.localizedDescription)")
    }

    return false
}

fileprivate func processCapture(_ sessionID: String) async -> Bool {
    // Create form data
    let fields: [MultipartForm.Field] = [
        .init(name: "session_id", text: sessionID)
    ]
    let form = MultipartForm(fields: fields)

    // Request type
    let url = URL(string: "\(AppConstants.apiBaseURL)/capture/process_completed_session")!
    var request = URLRequest(url: url)
    request.httpMethod = "POST"
    request.setValue("multipart/form-data;boundary=\(form.boundary)", forHTTPHeaderField: "Content-Type")

    // Try upload
    do
    {
        let (_, response) = try await URLSession.shared.upload(for: request, from: form.serialize())
        guard let response = response as? HTTPURLResponse,
            (200...299).contains(response.statusCode) else {
            if let response = response as? HTTPURLResponse {
                log("Error: Code \(response.statusCode)")
            } else {
                log("Error: Unknown error trying to communicate with server")
            }
            return false
        }
        log("Processed session \(sessionID) successfully")
        return true
    } catch {
        log("Error: Upload failed: \(error.localizedDescription)")
    }

    return false
}

fileprivate func getAudioFilesAscendingTimeOrder(fileExtension: String) -> [URL] {
    do {
        let documentDirectory = try FileManager.default.url(
            for: .documentDirectory,
            in: .userDomainMask,
            appropriateFor: nil,
            create: true
        )

        let directoryContents = try FileManager.default.contentsOfDirectory(
            at: documentDirectory,
            includingPropertiesForKeys: nil
        )

        return directoryContents.filter {
            // Must conform to naming convention established by AudioFileWriter
            AudioFileWriter.isValid(url: $0)
        }.sorted {
            // Sort ascending by timestamp and chunk number. Comparing filenames directly would
            // work only if all other metadata in filename is constant.
            let numericParts1 = "\(AudioFileWriter.getTimestamp(from: $0)!)_\(AudioFileWriter.getChunkNumber(from: $0)!)"
            let numericParts2 = "\(AudioFileWriter.getTimestamp(from: $1)!)_\(AudioFileWriter.getChunkNumber(from: $1)!)"
            return numericParts1 < numericParts2
        }
    } catch {
        log("Error getting files: \(error.localizedDescription)")
    }

    return []
}

fileprivate func deleteFile(_ url: URL) {
    do {
        try FileManager.default.removeItem(at: url)
        log("Deleted \(url)")
    } catch {
        log("Error: Failed to delete \(url)")
    }
}

fileprivate func deleteAllFiles(fileExtension: String) {
    do {
        let documentDirectory = try FileManager.default.url(
            for: .documentDirectory,
            in: .userDomainMask,
            appropriateFor: nil,
            create: true
        )

        let directoryContents = try FileManager.default.contentsOfDirectory(
            at: documentDirectory,
            includingPropertiesForKeys: nil
        )

        let fileExtension = ".\(fileExtension)"
        let files = directoryContents.filter { $0.pathExtension == fileExtension }

        for url in files {
            deleteFile(url)
        }
    } catch {
        log("Error deleting files: \(error.localizedDescription)")
    }
}
