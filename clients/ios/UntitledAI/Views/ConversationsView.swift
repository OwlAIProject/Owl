//
//  ConversationsView.swift
//  UntitledAI
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
            }
            .onDelete(perform: deleteConversation)
        }
        .refreshable {
            viewModel.fetchConversations()
        }
    }

    private func deleteConversation(at offsets: IndexSet) {
        guard let index = offsets.first else { return }
        viewModel.deleteConversation(viewModel.conversations[index])
    }
}

struct ConversationCellView: View {
    let conversation: Conversation
    
    private var formattedStartTime: String {
        conversation.startTime.formatted(date: .long, time: .shortened)
    }
    
    var body: some View {
        VStack(alignment: .leading, spacing: 5) {
            Text(formattedStartTime)
                .font(.subheadline)
                .foregroundColor(.secondary)
                .padding(.horizontal)
                .padding(.top)
            
            HStack(alignment: .top) {
                Text(conversation.shortSummary ?? conversation.summary)
                    .font(.headline)
                    .foregroundColor(.primary)
                    .lineLimit(3)
                    .truncationMode(.tail)
                    .padding()
                    .multilineTextAlignment(.leading)
                Spacer()
            }
        }
        .background(Color(.secondarySystemBackground))
        .cornerRadius(8)
    }
}
