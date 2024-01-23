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
        }
        .refreshable {
            viewModel.fetchConversations()
        }
    }
}

struct ConversationCellView: View {
    let conversation: Conversation

    var body: some View {
        HStack(alignment: .top) { 
            Text(conversation.summary)
                .font(.headline)
                .foregroundColor(.primary)
                .lineLimit(3)
                .truncationMode(.tail)
                .padding()
                .multilineTextAlignment(.leading)
            Spacer()
        }
        .background(Color(.secondarySystemBackground))
        .cornerRadius(8)
    }
}
