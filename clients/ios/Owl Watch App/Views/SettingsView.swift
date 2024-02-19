//
//  SettingsView.swift
//  Owl Watch App
//
//  Created by Bart Trzynadlowski on 1/24/24.
//

import SwiftUI

struct SettingsView: View {
    @Binding var isStreaming: Bool
    @Binding var isUploading: Bool

    var body: some View {
        VStack {
            Toggle("Live Stream", isOn: $isStreaming)
                .padding()
            Toggle("Upload", isOn: $isUploading)
                .disabled(isStreaming)
                .padding()

            Text("Capture Mode:")
            if isStreaming {
                Text("Live stream")
            } else {
                if isUploading {
                    Text("Spool and upload files")
                } else {
                    Text("Spool to disk")
                }
            }
        }
    }
}

#Preview {
    SettingsView(isStreaming: .constant(true), isUploading: .constant(true))
}
