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

    private func setupSocketListeners() {
        socketManager.socket.on("new_conversation") { [weak self] data, ack in
            guard let self = self else { return }
            if let conversationJsonString = data[0] as? String {
                let result: Result<Conversation, Error> = JSONDecoder.decode(Conversation.self, from: conversationJsonString)
                DispatchQueue.main.async {
                    switch result {
                    case .success(let conversation):
                        self.conversations.insert(conversation, at: 0)
                    case .failure(let error):
                        print("Decoding error: \(error)")
                    }
                }
            }
        }
    }
}
