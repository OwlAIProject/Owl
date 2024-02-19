//
//  FileUploadTask.swift
//  Owl
//
//  Created by Bart Trzynadlowski on 1/5/24.
//

//
// Overview
// --------
//
// Uploads capture files and requests processing when an entire capture has been uploaded. Captures
// are written to disk as a series of files (chunks), uploaded sequentially. This is 1) to make it
// simple to reason about what to upload next without requiring any back-and-forth with the server
// or additional metadata to be maintained, and 2) because it means completed chunks of compressed
// formats can be guaranteed to be valid and playable in case the most recent chunk is interrupted.
//
// Here is an outline of the process:
//
// 1. In-progress recordings are written with a .*-wip extension and contain capture UUID, start
//    timestamp, and sequential chunk number.
//
//      audio_6cea0828bbef11ee906aa67caffadefc_20240125-180400.123_0.pcm-wip
//
// 2. When completed, these are renamed with "-wip" being dropped. The chunks accumulate on disk
//    as the file upload task attempts to upload completed chunks in chronological order.
//
//      audio_6cea0828bbef11ee906aa67caffadefc_20240125-180400.123_0.pcm
//      audio_6cea0828bbef11ee906aa67caffadefc_20240125-180400.123_1.pcm
//      audio_6cea0828bbef11ee906aa67caffadefc_20240125-180400.123_2.pcm
//      audio_6cea0828bbef11ee906aa67caffadefc_20240125-180400.123_3.pcm-wip
//
// 3. If the capture is complete and no more files will be produced for it, an empty .end file
//    named with the capture UUID is written. Capture completion occurs when recording is
//    explicitly stopped or when the app first starts and discovers recordings on the disk leftover
//    from a previous session (which, if lacking a corresponding .end file, was interrupted). Below
//    is an example of a capture session with two remaining chunks left to upload that has been
//    marked as completed. Once the files are sent, processing will be requested and the .end file
//    will be removed.
//
//      audio_6cea0828bbef11ee906aa67caffadefc_20240125-180400.123_30.pcm
//      audio_6cea0828bbef11ee906aa67caffadefc_20240125-180400.123_31.pcm
//      6cea0828bbef11ee906aa67caffadefc.end
//
//    The completion file ensures that if the app crashes after all chunks have uploaded but before
//    processing has been triggered, it can be requested the next time the app launches.
//
//
// TODO:
// -----
//
// - Watch Connectivity for background transfers that are more reliable?
// - Need a flag to indicate whether file formats are frame-based (e.g., aac) or continuous (pcm).
//   For the latter, even .*-wip files can actually be uploaded but for the former, they would
//   likely contain incomplete frames.
//

import Foundation
import os

fileprivate var _uploadAllowed = true
fileprivate let _logger = Logger()

fileprivate func log(_ message: String) {
    _logger.notice("[FileUploadTask] \(message, privacy: .public)")
}

@MainActor
func runFileUploadTask(fileExtension: String) async {
    log("Starting upload task...")
    let contentType = "audio/\(fileExtension)"

    // Delete *.*-wip files that are incomplete
    deleteAllFiles(fileExtension: "\(fileExtension)-wip")

    // Get initial files left over from previous capture sessions. Mark them all completed because
    // these captures are definitely finished.
    let urls = getAudioFilesAscendingTimeOrder(fileExtension: fileExtension)
    for url in urls {
        guard let id = AudioFileWriter.getCaptureUUID(from: url) else {
            deleteFile(url) // remove files with ill-formatted names
            continue
        }
        markCaptureComplete(id)
    }

    while true {
        try? await Task.sleep(for: .seconds(5))
        guard _uploadAllowed else { continue }

        // Sample current files on disk and capture UUIDs known to be complete
        let completedChunkURLs = getAudioFilesAscendingTimeOrder(fileExtension: fileExtension)
        let allInProgressURLs = completedChunkURLs + getAudioFilesAscendingTimeOrder(fileExtension: "\(fileExtension)-wip")
        let completedCaptureUUIDs = getCompletedCaptureUUIDs()

        // Process any completed captures that have been completely uploaded
        guard _uploadAllowed else { continue }
        let processed = await tryProcessUploadedCaptures(
            existingURLs: allInProgressURLs,
            completedCaptureUUIDs: completedCaptureUUIDs
        )
        for id in processed {
            deleteCaptureCompletionFile(id)
        }

        // Upload each. Need to group by capture UUID because if any chunk fails, we need to skip
        // all subsequent files in capture to prevent chunks from being sent out of order. We
        // sorted by time earlier, files will remain in this order.
        guard _uploadAllowed else { continue }
        var urlsByCaptureUUID: [String: [URL]] = [:]
        for url in completedChunkURLs {
            guard let id = AudioFileWriter.getCaptureUUID(from: url) else {
                deleteFile(url)
                continue
            }
            var urls = urlsByCaptureUUID[id] == nil ? [] : urlsByCaptureUUID[id]!
            urls.append(url)
            urlsByCaptureUUID[id] = urls
        }
        for (_, urls) in urlsByCaptureUUID {
            for url in urls {
                let succeeded = await uploadFile(url, contentType: contentType)
                if succeeded {
                    deleteFile(url)
                } else {
                    // Skip remaining URLs for this capture to avoid uploading out of order
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

func markCaptureComplete(_ captureUUID: String) {
    // Mark completed captures by creating empty file named {capture_uuid}.end
    let url = URL.documents.appendingPathComponent("\(captureUUID).end")
    if !FileManager.default.createFile(atPath: url.path(percentEncoded: true), contents: nil, attributes: nil) {
        log("Failed to create completion file for capture: \(captureUUID)")
        return
    }
    log("Added \(captureUUID) to completed queue")
}

fileprivate func deleteCaptureCompletionFile(_ captureUUID: String) {
    let url = URL.documents.appendingPathComponent("\(captureUUID).end")
    deleteFile(url)
}

fileprivate func tryProcessUploadedCaptures(existingURLs urls: [URL], completedCaptureUUIDs: [String]) async -> [String] {
    // Once we have uploaded files that were marked completed, process them
    var captureUUIDsToProcess: [String] = []
    for id in completedCaptureUUIDs {
        let moreToUpload = urls.contains { AudioFileWriter.getCaptureUUID(from: $0) == id }
        if moreToUpload {
            log("Cannot process \(id) yet, there is more to upload")
            continue
        }

        // No matches on the file system, we've finished uploading this file completely. Process!
        log("Ready to process \(id)")
        captureUUIDsToProcess.append(id)
    }

    var captureUUIDsSuccessfullyProcessed: [String] = []
    for id in captureUUIDsToProcess {
        log("Processing \(id)...")
        if await processCapture(id) {
            captureUUIDsSuccessfullyProcessed.append(id)
        }
    }

    // Return what was processed
    return captureUUIDsSuccessfullyProcessed
}

fileprivate func uploadFile(_ url: URL, contentType: String) async -> Bool {
    guard let fileData = try? Data(contentsOf: url),
          let captureUUID = AudioFileWriter.getCaptureUUID(from: url),
          let timestamp = AudioFileWriter.getTimestamp(from: url) else {
        log("Error: Failed to load \(url) from disk")
        return false
    }

    let filename = url.lastPathComponent
    log("Uploading chunk \(filename)...")

    // Create form data
    let fields: [MultipartForm.Field] = [
        .init(name: "file", filename: filename, contentType: contentType, data: fileData),
        .init(name: "capture_uuid", text: captureUUID),
        .init(name: "timestamp", text: timestamp),
        .init(name: "device_type", text: "apple_watch")
    ]
    let form = MultipartForm(fields: fields)

    // Request type
    let url = URL(string: "\(AppConstants.apiBaseURL)/capture/upload_chunk")!
    var request = URLRequest(url: url)
    request.addCommonHeaders()
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

            // Despite error, server did respond, and we will not retry. It is not ujp to the
            // client to deal with internal server errors.
            return true
        }
        log("Uploaded file successfully")
        return true
    } catch {
        log("Error: Upload failed: \(error.localizedDescription)")
    }

    // Failed to even upload, client will keep trying until it can contact server
    return false
}

fileprivate func processCapture(_ captureUUID: String) async -> Bool {
    // Create form data
    let fields: [MultipartForm.Field] = [
        .init(name: "capture_uuid", text: captureUUID)
    ]
    let form = MultipartForm(fields: fields)

    // Request type
    let url = URL(string: "\(AppConstants.apiBaseURL)/capture/process_capture")!
    var request = URLRequest(url: url)
    request.addCommonHeaders()
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
            return true
        }
        log("Processed capture \(captureUUID) successfully")
        return true
    } catch {
        log("Error: Upload failed: \(error.localizedDescription)")
    }

    return false
}

fileprivate func getCompletedCaptureUUIDs() -> [String] {
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

        return directoryContents
            .compactMap {
                if $0.pathExtension == "end" {
                    let captureUUID = $0.deletingPathExtension().lastPathComponent
                    if captureUUID.count == 32 {
                        // Valid capture UUID is a 32-digit UUID
                        return captureUUID
                    }
                    return nil
                }
                return nil
            }
    } catch {
        log("Error getting files: \(error.localizedDescription)")
    }

    return []
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
            AudioFileWriter.isValid(url: $0) && $0.pathExtension == fileExtension
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

        let files = directoryContents.filter { $0.pathExtension == fileExtension }

        for url in files {
            deleteFile(url)
        }
    } catch {
        log("Error deleting files: \(error.localizedDescription)")
    }
}
