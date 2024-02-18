//
//  ContentView.swift
//  Owl Watch App
//
//  Created by ethan on 1/13/24.
//

import SwiftUI

struct ContentView: View {
    @State private var isCapturing: Bool = false
    @State private var isStreaming = false
    @State private var isUploading = true

    var body: some View {
        NavigationView {
            VStack {
                Button(action: toggleStreaming) {
                    Image(systemName: isCapturing ? "record.circle.fill" : "record.circle")
                        .imageScale(.large)
                        .foregroundStyle(.red)
                    Text(isCapturing ? "Stop" : "Record")
                }
            }
            .navigationTitle("Owl")
            .toolbar {
                ToolbarItem(placement: .bottomBar) {
                    NavigationLink {
                        SettingsView(isStreaming: $isStreaming, isUploading: $isUploading)
                    } label: {
                        Image(systemName: "gear")
                            .imageScale(.large)
                        Text("Settings")
                            .padding()
                    }
                }
            }
            .padding()
        }
        .onChange(of: isUploading, initial: true) {
            setUploadAllowed(to: isUploading)
        }
    }

    private func toggleStreaming() {
        if isCapturing {
            CaptureManager.shared.stopCapturing()
            isCapturing = false
        } else {
            CaptureManager.shared.startCapturing(stream: isStreaming)
            isCapturing = true
        }
    }
}

#Preview {
    ContentView()
}
