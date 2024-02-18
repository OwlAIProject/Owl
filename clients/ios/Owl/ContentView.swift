//
//  ContentView.swift
//  Owl
//
//  Created by ethan on 1/13/24.
//

import SwiftUI

struct ContentView: View {
    @ObservedObject var viewModel = ConversationsViewModel()

    var body: some View {
        NavigationView {
            ConversationsView(viewModel: viewModel)
                .navigationTitle("Conversations")
                .navigationBarItems(trailing: BadgeView())
        }
    }

}

struct BadgeView: View {
    @ObservedObject var captureManager = CaptureManager.shared
    @ObservedObject var bleManager = BLEManager.shared

    var body: some View {
        Group {
            if let deviceName = captureManager.currentCapture?.deviceName {
                DeviceBannerView(deviceName: deviceName, batteryLevel: bleManager.batteryLevel, isCharging: bleManager.isCharging, isAwaitingReconnection: captureManager.isAwaitingReconnection)
            }
        }
    }
}

struct ContentView_Previews: PreviewProvider {
    static var previews: some View {
        ContentView()
    }
}
