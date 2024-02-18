//
//  ConversationsView.swift
//  Owl
//
//  Created by ethan on 1/23/24.
//

import Foundation
import SwiftUI

struct ConversationsView: View {
    @ObservedObject var viewModel: ConversationsViewModel

    var body: some View {
        List {
            ForEach(viewModel.conversations, id: \.id) { conversation in
                NavigationLink(destination: ConversationDetailView(conversation: conversation)) {
                    ConversationCellView(conversation: conversation)
                }
                .swipeActions(edge: .trailing, allowsFullSwipe: false) {
                    Button(role: .destructive) {
                        if let index = viewModel.conversations.firstIndex(where: { $0.id == conversation.id }) {
                            viewModel.deleteConversation(viewModel.conversations[index])
                        }
                    } label: {
                        Label("Delete", systemImage: "trash")
                    }
                    
                    if conversation.state == .capturing {
                        Button {
                            viewModel.endConversation(conversation)
                        } label: {
                            Label("End", systemImage: "stop.fill")
                        }
                        .tint(.orange)
                    } else {
                        Button {
                            viewModel.retryConversation(conversation)
                        } label: {
                            Label("Retry", systemImage: "arrow.clockwise")
                        }
                        .tint(.blue)
                    }
                }
            }
        }
        .refreshable {
            viewModel.fetchConversations()
        }
    }

    private func deleteConversation(at offsets: IndexSet) {
        viewModel.conversations.remove(atOffsets: offsets)
    }
}

struct CountUpTimerView: View {
    let startTime: Date
    @State private var currentTime = Date()
    
    private var timeFormatter: DateFormatter {
        let formatter = DateFormatter()
        formatter.timeStyle = .medium
        return formatter
    }
    
    private var elapsedTime: String {
        let interval = Date().timeIntervalSince(startTime)
        let hours = Int(interval) / 3600
        let minutes = Int(interval) / 60 % 60
        let seconds = Int(interval) % 60
        return String(format: "%02i:%02i:%02i", hours, minutes, seconds)
    }
    
    private let timer = Timer.publish(every: 1, on: .main, in: .common).autoconnect()
    
    var body: some View {
        Text(elapsedTime)
            .font(.headline.monospacedDigit())
            .foregroundColor(.blue)
            .padding(.vertical, 8)
            .padding(.horizontal, 12)
            .background(Color(.systemBackground))
            .cornerRadius(8)
            .shadow(radius: 3)
            .overlay(
                RoundedRectangle(cornerRadius: 8)
                    .stroke(Color.blue, lineWidth: 2)
            )
            .onReceive(timer) { _ in
                self.currentTime = Date()
            }
            .animation(.easeInOut, value: currentTime)
            .transition(.opacity)
    }
}

struct ConversationStateBadgeView: View {
    let state: ConversationState
    
    private func badgeColor() -> Color {
        switch state {
        case .capturing:
            return .blue
        case .processing:
            return .orange
        case .completed:
            return .green
        case .failedProcessing:
            return .red
        }
    }
    
    private func badgeText() -> String {
        switch state {
        case .failedProcessing:
            return "Failed"
        default:
            return state.rawValue
        }
    }
    
    var body: some View {
        Text(badgeText())
            .font(.caption)
            .fontWeight(.bold)
            .foregroundColor(.white)
            .padding(.horizontal, 8)
            .padding(.vertical, 4)
            .background(badgeColor())
            .cornerRadius(10)
    }
}

struct ConversationCellView: View {
    let conversation: Conversation
    
    private var formattedStartTime: String {
        conversation.startTime.formatted(date: .numeric, time: .shortened)
    }
    
    var body: some View {
        VStack(alignment: .leading, spacing: 5) {
            HStack {
                Text(formattedStartTime)
                    .font(.subheadline)
                    .foregroundColor(.secondary)
                    .padding(.horizontal)
                    .padding(.top)
                
                Spacer()
                
                ConversationStateBadgeView(state: conversation.state)
                    .padding(.top)
                    .padding(.horizontal)
            }
            
            if conversation.state == .capturing {
                CountUpTimerView(startTime: conversation.startTime)
                    .padding(.horizontal)
            } else {
                HStack(alignment: .top) {
                    Text(conversation.shortSummary ?? conversation.summary ?? "")
                        .font(.headline)
                        .foregroundColor(.primary)
                        .lineLimit(3)
                        .truncationMode(.tail)
                        .padding()
                        .multilineTextAlignment(.leading)
                    Spacer()
                }
            }
           
        }
        .background(Color(.secondarySystemBackground))
        .cornerRadius(8)
    }
}

