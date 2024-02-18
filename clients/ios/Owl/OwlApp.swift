//
//  OwlApp.swift
//  Owl
//
//  Created by ethan on 1/13/24.
//

import SwiftUI

class AppDelegate: NSObject, UIApplicationDelegate {

    func application(_ application: UIApplication, didFinishLaunchingWithOptions launchOptions: [UIApplication.LaunchOptionsKey: Any]?) -> Bool {
        _ = SocketManager.shared
        _ = WatchConnectivityManager.shared
        if AppConstants.locationReportingEnabled {
            let locationManager = LocationManager.shared
            locationManager.startLocationUpdates()
        }
        return true
    }
}


@main
struct OwlApp: App {
    @UIApplicationDelegateAdaptor(AppDelegate.self) var appDelegate
    private var ble = BLEManager.shared
    var body: some Scene {
        WindowGroup {
            ContentView()
        }
    }
}
