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
//                self?.conversationsInProgress = response.conversationsInProgress.filter { $0.inConversation }
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

    func retryConversation(_ conversation: Conversation) {
        apiService.retryConversation(conversation.id) { [weak self] success in
           
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
        
        socketManager.socket.on("update_conversation") { [weak self] data, ack in
            guard let self = self else { return }

            if let conversationJsonString = data[0] as? String,
               let jsonData = conversationJsonString.data(using: .utf8) {
                do {
                    print("Received conversation JSON string: \(conversationJsonString)")

                    let decoder = JSONDecoder.dateDecoder()
                    let updatedConversation = try decoder.decode(Conversation.self, from: jsonData)
                    DispatchQueue.main.async {
                        if let index = self.conversations.firstIndex(where: { $0.id == updatedConversation.id }) {
                            self.conversations[index] = updatedConversation
                        } else {
                            self.conversations.insert(updatedConversation, at: 0)
                        }
                    }
                } catch {
                    print("Decoding error: \(error)")
                }
            }
        }
        
        socketManager.socket.on("delete_conversation") { [weak self] data, ack in
            guard let self = self else { return }

            if let conversationJsonString = data[0] as? String,
               let jsonData = conversationJsonString.data(using: .utf8) {
                do {
                    print("Received conversation JSON string: \(conversationJsonString)")
                    let decoder = JSONDecoder.dateDecoder()
                    let deletedConversation = try decoder.decode(Conversation.self, from: jsonData)
                    DispatchQueue.main.async {
                        if let index = self.conversations.firstIndex(where: { $0.id == deletedConversation.id }) {
                            self.conversations.remove(at: index)
                            print("Deleted conversation with ID: \(deletedConversation.id)")
                        } else {
                            print("Conversation with ID: \(deletedConversation.id) not found for deletion.")
                        }
                    }
                } catch {
                    print("Decoding error: \(error)")
                }
            }
        }
        
        socketManager.socket.on("new_utterance") { [weak self] data, ack in
            guard let self = self,
                  let dataArray = data[0] as? [String: Any],
                  let conversationUUID = dataArray["conversation_uuid"] as? String,
                  let utteranceJson = dataArray["utterance"] as? String,
                  let jsonData = utteranceJson.data(using: .utf8) else { return }

            do {
                let decoder = JSONDecoder.dateDecoder()
                let newUtterance = try decoder.decode(Utterance.self, from: jsonData)
                DispatchQueue.main.async {
                    if let index = self.conversations.firstIndex(where: { $0.conversationUUID == conversationUUID }) {
                        var conversation = self.conversations[index]
                        if let rtIndex = conversation.transcriptions.firstIndex(where: { $0.realtime }) {
                            conversation.transcriptions[rtIndex].utterances.append(newUtterance)
                        }
                        self.conversations[index] = conversation
                    }
                }
            } catch {
                print("Decoding error for new utterance: \(error)")
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
