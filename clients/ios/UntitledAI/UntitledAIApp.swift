//
//  UntitledAIApp.swift
//  UntitledAI
//
//  Created by ethan on 1/13/24.
//

import SwiftUI

class AppDelegate: NSObject, UIApplicationDelegate {

    func application(_ application: UIApplication, didFinishLaunchingWithOptions launchOptions: [UIApplication.LaunchOptionsKey: Any]?) -> Bool {
        _ = SocketManager.shared
        _ = BLEManager.shared
        return true
    }
}


@main
struct UntitledAIApp: App {
    @UIApplicationDelegateAdaptor(AppDelegate.self) var appDelegate
    var body: some Scene {
        WindowGroup {
            ContentView()
        }
    }
}
