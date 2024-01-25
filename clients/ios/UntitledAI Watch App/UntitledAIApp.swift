//
//  UntitledAIApp.swift
//  UntitledAI Watch App
//
//  Created by ethan on 1/13/24.
//

import SwiftUI

@main
struct UntitledAI_Watch_AppApp: App {
    var body: some Scene {
        WindowGroup {
            ContentView()
                .task {
                    await runFileUploadTask(fileExtension: "pcm")
                }
        }
    }
}
