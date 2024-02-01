//
//  ConversationsViewModel.swift
//  UntitledAI
//
//  Created by ethan on 1/23/24.
//
import Foundation
class ConversationsViewModel: ObservableObject {
    @Published var conversations: [Conversation] = []

    private let apiService = API.shared 
    private let socketManager = SocketManager.shared

    init() {
        fetchConversations()
        setupSocketListeners()
    }

    func fetchConversations() {
        apiService.fetchConversations { [weak self] response in
            DispatchQueue.main.async {
                self?.conversations = response.conversations
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
    }
}
