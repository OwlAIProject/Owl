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
        return true
    }
}


@main
struct UntitledAIApp: App {
    @ObservedObject var ble = BLEManager.shared
    @UIApplicationDelegateAdaptor(AppDelegate.self) var appDelegate
    var body: some Scene {
        WindowGroup {
            ContentView()
        }
    }
}
