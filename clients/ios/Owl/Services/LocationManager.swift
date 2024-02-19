//
//  LocationManager.swift
//  Owl
//
//  Created by ethan on 1/25/24.
//

import Foundation
import CoreLocation

// TODO Optimize this
class LocationManager: NSObject, CLLocationManagerDelegate {
    static let shared = LocationManager()
    private let locationManager = CLLocationManager()
    private var timer: Timer?
    var reportingInterval: TimeInterval = AppConstants.locationReportingInterval

    override init() {
        super.init()
        locationManager.delegate = self
        self.locationManager.requestAlwaysAuthorization()
        self.locationManager.allowsBackgroundLocationUpdates = true
    }

    func startLocationUpdates() {
        DispatchQueue.global(qos: .default).async {
            guard CLLocationManager.locationServicesEnabled() else { return }
            
            DispatchQueue.main.async {
                self.locationManager.startUpdatingLocation()
                self.timer = Timer.scheduledTimer(timeInterval: self.reportingInterval, target: self, selector: #selector(self.updateLocation), userInfo: nil, repeats: true)
            }
        }
    }
    
    @objc private func updateLocation() {
        guard let currentLocation = locationManager.location else { return }
        getPlacemark(forLocation: currentLocation) { placemark in
            guard let placemark = placemark else { return }

            // Sometimes these can be the same
            var streetAddress = ""
            if let subThoroughfare = placemark.subThoroughfare, let thoroughfare = placemark.thoroughfare, subThoroughfare != thoroughfare {
                streetAddress = subThoroughfare + " " + thoroughfare
            } else {
                streetAddress = placemark.thoroughfare ?? placemark.subThoroughfare ?? ""
            }

            var addressParts: [String?] = [
                streetAddress,
                placemark.locality,
                placemark.subLocality,
                placemark.administrativeArea,
                placemark.subAdministrativeArea,
                placemark.postalCode,
                placemark.country,
                placemark.inlandWater,
                placemark.ocean
            ]

            if let areasOfInterest = placemark.areasOfInterest, !areasOfInterest.isEmpty {
                addressParts.append(contentsOf: areasOfInterest)
            }

            let addressString = addressParts.compactMap { $0 }.joined(separator: ", ")

            print("Location: \(currentLocation), Address: \(addressString)")

            let location = Location(latitude: currentLocation.coordinate.latitude,
                                    longitude: currentLocation.coordinate.longitude,
                                    address: addressString,
                                    captureUUID: CaptureManager.shared.currentCapture?.captureUUID
            )

            API.shared.saveLocation(location) { result in
                switch result {
                case .success(_):
                    print("Location saved successfully.")
                case .failure(let error):
                    print("Error saving location: \(error.localizedDescription)")
                }
            }
        }
    }


    private func getPlacemark(forLocation location: CLLocation, completionHandler: @escaping (CLPlacemark?) -> Void) {
        let geocoder = CLGeocoder()
        geocoder.reverseGeocodeLocation(location) { placemarks, error in
            if let error = error {
                print("Error in reverseGeocode: \(error)")
                completionHandler(nil)
                return
            }
            completionHandler(placemarks?.first)
        }
    }

    func locationManagerDidChangeAuthorization(_ manager: CLLocationManager) {
        switch manager.authorizationStatus {
            case .authorizedAlways, .authorizedWhenInUse:
                startLocationUpdates()
            case .denied, .restricted, .notDetermined:
                break
            @unknown default:
                break
        }
    }
    
    func sendCurrentLocation() {
        guard let _ = locationManager.location else {
            print("Current location not available")
            return
        }
        updateLocation()
    }

}
