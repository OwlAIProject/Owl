//
//  ContentView.swift
//  UntitledAI Watch App
//
//  Created by ethan on 1/13/24.
//

import SwiftUI

struct ContentView: View {
    @State private var isStreaming: Bool = false

    var body: some View {
        VStack {
            Text("UntitledAI")

            Button(action: toggleStreaming) {
                Text(isStreaming ? "Stop Capturing" : "Start Capturing")
            }
        }
        .padding()
    }

    private func toggleStreaming() {
        if isStreaming {
            CaptureManager.shared.stopCapturing()
            isStreaming = false
        } else {
            CaptureManager.shared.startCapturing()
            isStreaming = true
        }
    }
}

#Preview {
    ContentView()
}
