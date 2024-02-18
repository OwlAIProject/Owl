//
//  OwlWatchApp.swift
//  Owl Watch App
//
//  Created by ethan on 1/13/24.
//

import SwiftUI

@main
struct OwlWatchApp: App {
    init() {
        _ = WatchConnectivityManager.shared
    }
    var body: some Scene {
        WindowGroup {
            ContentView()
                .task {
                    await runFileUploadTask(fileExtension: "pcm")
                }
        }
    }
}
