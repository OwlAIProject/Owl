//
//  API.swift
//  UntitledAI
//
//  Created by ethan on 1/23/24.
//

import Foundation
class API {
    static let shared = API()
    
    private init() {}

    func fetchConversations(completionHandler: @escaping (ConversationsResponse) -> Void) {
        guard let url = URL(string: "\(AppConstants.apiBaseURL)/conversations/") else { return }

        let task = URLSession.shared.dataTask(with: url) { (data, response, error) in
            if let error = error {
                print("Error: \(error)")
            } else if let data = data {
                do {
                    let conversationsResponse = try JSONDecoder().decode(ConversationsResponse.self, from: data)
                    completionHandler(conversationsResponse)
                } catch {
                    print("Unable to decode, \(error)")
                }
            }
        }
        task.resume()
    }
}
