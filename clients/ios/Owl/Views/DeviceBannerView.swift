//
//  DeviceBannerView.swift
//  Owl
//
//  Created by ethan on 2/16/24.
//

import Foundation
import SwiftUI

struct DeviceBannerView: View {
    let deviceName: String
    let batteryLevel: Int?
    let isCharging: Bool?
    let isAwaitingReconnection: Bool

    var body: some View {
        HStack(alignment: .center, spacing: 4) {
            Text(deviceName)
                .font(.system(size: 16, weight: .medium, design: .rounded))
                .foregroundColor(Color.primary.opacity(0.7))
                .padding(.vertical, 8)
                .padding(.horizontal, 12)
                .fixedSize(horizontal: false, vertical: true)
                .lineLimit(1)
                .minimumScaleFactor(0.5)
            
            if let batteryLevel = batteryLevel, let isCharging = isCharging {
                HStack(spacing: 4) {
                    Image(systemName: isCharging ? "battery.100.bolt" : batteryIcon(batteryLevel: batteryLevel))
                        .foregroundColor(isCharging ? .green : batteryLevelColor(percentage: batteryLevel))
                        .imageScale(.small)
                        .transition(.scale.combined(with: .opacity))
                        .animation(.easeInOut(duration: 0.5), value: batteryLevel)

                    Text("\(batteryLevel)%")
                        .font(.system(size: 14, weight: .semibold, design: .rounded))
                        .foregroundColor(.primary)
                        .fixedSize(horizontal: false, vertical: true)
                        .lineLimit(1)
                        .minimumScaleFactor(0.5)
                        .transition(.scale.combined(with: .opacity))
                        .animation(.easeInOut(duration: 0.5), value: batteryLevel)
                }
                .padding(.vertical, 6)
                .padding(.horizontal, 8)
                .accessibilityElement(children: .combine)
                .transition(.opacity.combined(with: .scale))
            }

            if isAwaitingReconnection {
                ProgressView()
                    .progressViewStyle(CircularProgressViewStyle(tint: .blue))
                    .scaleEffect(0.5)
                    .transition(.opacity.combined(with: .scale))
                    .animation(.easeInOut(duration: 0.5), value: isAwaitingReconnection)
            }
        }
        .padding(.horizontal)
        .background(LinearGradient(gradient: Gradient(colors: [Color.white.opacity(0.3), Color.gray.opacity(0.1)]), startPoint: .leading, endPoint: .trailing))
        .cornerRadius(20)
        .shadow(radius: 1)
        .padding(.horizontal)
        .padding(.vertical, 4)
    }

    private func batteryIcon(batteryLevel: Int) -> String {
        switch batteryLevel {
        case 0...20: return "battery.0"
        case 21...40: return "battery.25"
        case 41...60: return "battery.50"
        case 61...80: return "battery.75"
        default: return "battery.100"
        }
    }

    private func batteryLevelColor(percentage: Int) -> Color {
        switch percentage {
        case 0...20: return .red
        case 21...40: return .orange
        case 41...100: return .green
        default: return .gray
        }
    }
}

