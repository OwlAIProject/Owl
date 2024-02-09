//
//  ConversationsViewModel.swift
//  UntitledAI
//
//  Created by ethan on 1/23/24.
//
import Foundation
class ConversationsViewModel: ObservableObject {
    @Published var conversations: [Conversation] = []
    @Published var conversationsInProgress: [ConversationProgress] = []

    private let apiService = API.shared 
    private let socketManager = SocketManager.shared

    init() {
        fetchConversations()
        setupSocketListeners()
    }

    func fetchConversations() {
        apiService.fetchConversations { [weak self] response in
            DispatchQueue.main.async {
                // These are snapshots and safe to overwrite anything that was added incrementally
                // by the socket listeners
                self?.conversations = response.conversations
                self?.conversationsInProgress = response.conversationsInProgress.filter { $0.inConversation }
            }
        }
    }
    
    func deleteConversation(_ conversation: Conversation) {
        apiService.deleteConversation(conversation.id) { [weak self] success in
            DispatchQueue.main.async {
                if success {
                    self?.conversations.removeAll { $0.id == conversation.id }
                }
            }
        }
    }
    
    private func setupSocketListeners() {
        socketManager.socket.on("new_conversation") { [weak self] data, ack in
            guard let self = self else { return }

            if let conversationJsonString = data[0] as? String,
               let jsonData = conversationJsonString.data(using: .utf8) {
                do {
                    let decoder = JSONDecoder.dateDecoder()
                    let conversation = try decoder.decode(Conversation.self, from: jsonData)
                    DispatchQueue.main.async {
                        self.conversations.insert(conversation, at: 0)
                    }
                } catch {
                    print("Decoding error: \(error)")
                }
            }
        }

        socketManager.socket.on("conversation_progress") { [weak self] data, ack in
            guard let self = self else { return }

            if let conversationProgressJsonString = data[0] as? String,
               let jsonData = conversationProgressJsonString.data(using: .utf8) {
                do {
                    let decoder = JSONDecoder.dateDecoder()
                    let conversationInProgress = try decoder.decode(ConversationProgress.self, from: jsonData)
                    DispatchQueue.main.async {
                        print(conversationInProgress)
                        // Replace/remove existing if it exists, otherwise insert new
                        if let idx = self.conversationsInProgress.firstIndex(where: { $0.conversationUUID == conversationInProgress.conversationUUID }) {
                            var modified = self.conversationsInProgress
                            modified[idx] = conversationInProgress
                            self.conversationsInProgress = modified.filter { $0.inConversation }    // remove anything not in progress
                        } else if conversationInProgress.inConversation {
                            self.conversationsInProgress.insert(conversationInProgress, at: 0)
                        }
                    }
                } catch {
                    print("Decoding error: \(error)")
                }
            }
        }
    }
}
