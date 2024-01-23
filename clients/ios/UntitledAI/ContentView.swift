//
//  ContentView.swift
//  UntitledAI
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
    @ObservedObject var bleManager = BLEManager.shared

    var body: some View {
        Group {
            if let deviceName = bleManager.connectedDeviceName {
                DeviceBannerView(deviceName: deviceName)
            }
        }
    }
}

struct DeviceBannerView: View {
    let deviceName: String

    var body: some View {
        Text(deviceName)
            .font(.caption)
            .fontWeight(.bold)
            .foregroundColor(.white)
            .padding(.horizontal, 10)
            .padding(.vertical, 5)
            .background(Color.blue)
            .cornerRadius(10)
            .overlay(
                RoundedRectangle(cornerRadius: 10)
                    .stroke(Color.white, lineWidth: 2)
            )
    }
}

struct ContentView_Previews: PreviewProvider {
    static var previews: some View {
        ContentView()
    }
}
