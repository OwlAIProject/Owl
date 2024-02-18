//
//  NetworkManager.swift
//  Owl Watch App
//
//  Created by ethan on 1/13/24.
//
import Foundation

class NetworkManager : NSObject, URLSessionDataDelegate {
    static var shared = NetworkManager()
    private let bufferQueue = DispatchQueue(label: "com.owl.networkManagerBufferQueue")
    private var urlSession: URLSession! = nil
    private var captureUUID: String?
    private var streamingTask: URLSessionDataTask? = nil
    
    var isStreaming: Bool { return self.streamingTask != nil }
    
    func connect(captureUUID: String?) {
        guard let captureUUID else {
            print("Capture UUID is nil")
            return
        }
        let config = URLSessionConfiguration.default
        config.requestCachePolicy = .reloadIgnoringLocalCacheData
        self.urlSession = URLSession(configuration: config, delegate: self, delegateQueue: .main)
        var components = URLComponents(string: "\(AppConstants.apiBaseURL)/capture/streaming_post/\(captureUUID)")
        components?.queryItems = [
            URLQueryItem(name: "device_type", value: "apple_watch")
        ]
        guard let url = components?.url else {
            fatalError("Invalid URL")
        }
        var request = URLRequest(url: url)
        request.addCommonHeaders()
        request.httpMethod = "POST"
        request.setValue("application/octet-stream", forHTTPHeaderField: "Content-Type")
        let task = self.urlSession.uploadTask(withStreamedRequest: request)
        self.streamingTask = task
        task.resume()
    }
    
    func startStreaming() {
        captureUUID = UUID().hex
        let message = ["event": "startedStreaming", "captureUUID": captureUUID!]
        WatchConnectivityManager.shared.sendMessage(message)
        connect(captureUUID: captureUUID!)
    }
    
    func stopStreaming() {
        guard let task = self.streamingTask else {
            return
        }
        guard let captureUUID else {
            print("Capture UUID is nil")
            return
        }
        

        self.streamingTask = nil
        task.cancel()
        self.closeStream()
        self.urlSession = nil
        let url = URL(string: "\(AppConstants.apiBaseURL)/capture/streaming_post/\(captureUUID)/complete")!
        
        // Signal end
        var request = URLRequest(url: url)
        request.addCommonHeaders()
        request.httpMethod = "POST"
        let config = URLSessionConfiguration.default
        let session = URLSession(configuration: config)
        let postTask = session.dataTask(with: request) { data, response, error in
            if let error = error {
                print("Error occurred while sending completion signal: \(error)")
                return
            }
            print("Completion signal sent successfully.")
        }
        postTask.resume()
        self.captureUUID = nil
    }
    
    var outputStream: OutputStream? = nil
    
    private func closeStream() {
        if let stream = self.outputStream {
            stream.close()
            self.outputStream = nil
        }
    }
    
    func urlSession(_ session: URLSession, task: URLSessionTask, needNewBodyStream completionHandler: @escaping (InputStream?) -> Void) {
        self.closeStream()
        
        var inStream: InputStream? = nil
        var outStream: OutputStream? = nil
        
        // Create bound input and output streams
        Stream.getBoundStreams(withBufferSize: 96000, inputStream: &inStream, outputStream: &outStream)
        
        // Open the output stream
        if let outStream = outStream {
            outStream.open()
            self.outputStream = outStream
        }
        // Provide the input stream to the completion handler
        completionHandler(inStream)
    }
    
    func urlSession(_ session: URLSession, dataTask: URLSessionDataTask, didReceive data: Data) {
        NSLog("task data: %@", data as NSData)
    }
    
    func urlSession(_ session: URLSession, task: URLSessionTask, didCompleteWithError error: Error?) {
        if let error = error as NSError? {
            NSLog("task error: %@ / %d", error.domain, error.code)
        } else {
            NSLog("task complete")
        }
    }
}

extension NetworkManager {
    func writeData(_ data: Data) {
        bufferQueue.async {
            guard let outputStream = self.outputStream, outputStream.streamStatus == .open else {
                //print("Output stream is not open")
                return
            }
            data.withUnsafeBytes { buffer in
                guard let bytes = buffer.bindMemory(to: UInt8.self).baseAddress else {
                    print("Unable to bind memory")
                    return
                }
                var bytesLeft = data.count
                while bytesLeft > 0 {
                    let bytesWritten = outputStream.write(bytes, maxLength: bytesLeft)
                    if bytesWritten < 0, let error = outputStream.streamError {
                        print("Stream write error: \(error)")
                        break
                    }
                    bytesLeft -= bytesWritten
                }
            }
        }
    }
}
