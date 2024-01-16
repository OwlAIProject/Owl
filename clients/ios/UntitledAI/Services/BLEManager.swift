//
//  BLEManager.swift
//  UntitledAI
//
//  Created by ethan on 1/15/24.
//

import Foundation
import CoreBluetooth
//
//class BLEManager: NSObject, CBCentralManagerDelegate, CBPeripheralDelegate, ObservableObject {
//    var centralManager: CBCentralManager!
//    var myPeripheral: CBPeripheral?
//    let audioCharacteristicUUID = CBUUID(string: "b189a505-a86c-11ee-a5fb-8f2089a49e7e")
//       let imageCharacteristicUUID = CBUUID(string: "838e37a0-f284-490f-8e1f-8d53b385d1cd")
//    private var imageData = Data()
//    private var frameSequencer: FrameSequencer?
//    static let shared = BLEManager()
//    @Published var dataSpeed: String = ""
//    private var startTime: TimeInterval?
//    private var totalDataSize: Int = 0
//    private let socketManager = SocketManager.shared
//    //
//    override init() {
//        super.init()
//        centralManager = CBCentralManager(delegate: self, queue: nil, options: [CBCentralManagerOptionRestoreIdentifierKey: "myCentralManagerIdentifier2"])
//
//    }
//
//    func centralManagerDidUpdateState(_ central: CBCentralManager) {
//          if central.state == .poweredOn {
//              retrieveConnectedPeripherals()
//              scanForPeripherals()
//          }
//      }
//
//      private func retrieveConnectedPeripherals() {
//          let connectedPeripherals = centralManager.retrieveConnectedPeripherals(withServices: [CBUUID(string: "03d5d5c4-a86c-11ee-9d89-8f2089a49e7e")])
//          for peripheral in connectedPeripherals {
//              myPeripheral = peripheral
//              myPeripheral!.delegate = self
//              centralManager.connect(myPeripheral!, options: nil)
//          }
//      }
//    func scanForPeripherals() {
//        print("Starting scan for peripherals")
//        centralManager.scanForPeripherals(withServices: [CBUUID(string: "03d5d5c4-a86c-11ee-9d89-8f2089a49e7e")], options: [CBCentralManagerScanOptionAllowDuplicatesKey: NSNumber(value: true)])
//        DispatchQueue.main.asyncAfter(deadline: .now() + 10) { [weak self] in
//            guard let self = self else { return }
//            if self.myPeripheral == nil {
//                print("No peripherals found, restarting scan")
//                self.scanForPeripherals()
//            }
//        }
//    }
//    func centralManager(_ central: CBCentralManager, didDiscover peripheral: CBPeripheral, advertisementData: [String: Any], rssi RSSI: NSNumber) {
//        print("didDiscover")
//
//        if myPeripheral == nil {
//            myPeripheral = peripheral
//            myPeripheral!.delegate = self
//            centralManager.connect(myPeripheral!, options: nil)
//        } else if myPeripheral?.identifier == peripheral.identifier, myPeripheral?.state != .connected {
//            centralManager.connect(myPeripheral!, options: nil)
//        }
//        // Stop scanning as we are only interested in one specific peripheral
//        centralManager.stopScan()
//    }
//
//
//    func centralManager(_ central: CBCentralManager, didConnect peripheral: CBPeripheral) {
//        print("Peripheral connected")
//        peripheral.discoverServices([CBUUID(string: "03d5d5c4-a86c-11ee-9d89-8f2089a49e7e")])
//        frameSequencer = FrameSequencer()
//    }
//
//
//    func peripheral(_ peripheral: CBPeripheral, didDiscoverServices error: Error?) {
//        print("didDiscoverServices")
//        guard let services = peripheral.services else { return }
////        for service in services {
////            // Discover both audio and image characteristics
////            let characteristicUUIDs = [
////                CBUUID(string: "beb5483e-36e1-4688-b7f5-ea07361b26a8"), // Audio characteristic UUID
////              //  CBUUID(string: "838e37a0-f284-490f-8e1f-8d53b385d1cd")  // Image characteristic UUID
////            ]
////            peripheral.discoverCharacteristics(characteristicUUIDs, for: service)
////        }
//        for service in services {
//               // Discover all characteristics for each service
//               peripheral.discoverCharacteristics(nil, for: service)
//           }
//    }
//
////    func peripheral(_ peripheral: CBPeripheral, didUpdateNotificationStateFor characteristic: CBCharacteristic, error: Error?) {
////        if let error = error {
////            print("Error changing notification state: \(error.localizedDescription)")
////        } else {
////            print("Notification state updated for \(characteristic.uuid): \(characteristic.isNotifying)")
////        }
////    }
//    func peripheral(_ peripheral: CBPeripheral, didDiscoverCharacteristicsFor service: CBService, error: Error?) {
//        print("didDiscoverCharacteristicsFor")
//        print(service.characteristics)
//        guard let characteristics = service.characteristics else { return }
//        for characteristic in characteristics {
//            if characteristic.uuid.isEqual(audioCharacteristicUUID) || characteristic.uuid.isEqual(imageCharacteristicUUID) {
//                if characteristic.properties.contains(.notify) {
//                    print("Subscribing to characteristic \(characteristic.uuid)")
//                    peripheral.setNotifyValue(true, for: characteristic)
//                } else {
//                    print("Characteristic does not support notifications")
//                }
//            }
//        }
//    }
//
//
//    func peripheral(_ peripheral: CBPeripheral, didUpdateValueFor characteristic: CBCharacteristic, error: Error?) {
//        if let error = error {
//            print("Error updating value: \(error.localizedDescription)")
//            return
//        }
//
//        guard let value = characteristic.value else {
//            print("No value received")
//            return
//        }
//        if characteristic.uuid.isEqual(imageCharacteristicUUID) {
//              // Handle image data
////              imageData.append(value)
////
////              // Check if this is the final packet (less than 182 bytes)
////              if value.count < 182 {
////                  // Convert the imageData to UIImage
////                  if let image = UIImage(data: imageData) {
////                      DispatchQueue.main.async {
////                          self.receivedImage = image // Update your published UIImage property
////                      }
////                  } else {
////                      print("Error: Data could not be converted to an image.")
////                  }
////                  imageData = Data() // Reset imageData for the next image
////              }
//          }  else if characteristic.uuid.isEqual(audioCharacteristicUUID) {
//                              if let  completeFrames = frameSequencer?.add(packet: value) {
//                                  for frame in completeFrames {
//                                      // Send each complete frame to the server
//                                      print("received")
//                                      print(frame)
//                                      socketManager.sendAudioData(frame)
//                                  }
//                              }
//            }
//        if let data = characteristic.value {
//               // Start the timer if it's not started yet
//               if startTime == nil {
//                   startTime = Date().timeIntervalSince1970
//               }
//
//               // Update total data size
//               totalDataSize += data.count
//
//               // Calculate the time elapsed
//               if let startTime = startTime {
//                   let timeElapsed = Date().timeIntervalSince1970 - startTime
//                   if timeElapsed > 0 {
//                       let speed = Double(totalDataSize) / timeElapsed / 1024 // Convert to KB/s
//                       print( String(format: "%.2f KB/s", speed))
////                       DispatchQueue.main.async {
////                           self.dataSpeed = String(format: "%.2f KB/s", speed)
////                       }
//                   }
//               }
//           }
//    }
//
//    func centralManager(_ central: CBCentralManager, willRestoreState dict: [String: Any]) {
//        if let restoredPeripherals = dict[CBCentralManagerRestoredStatePeripheralsKey] as? [CBPeripheral] {
//            for peripheral in restoredPeripherals {
//                myPeripheral = peripheral
//                myPeripheral!.delegate = self
//
//                if peripheral.state == .connected {
//                    peripheral.discoverServices([CBUUID(string: "03d5d5c4-a86c-11ee-9d89-8f2089a49e7e")])
//                } else if peripheral.state == .disconnected {
//                    centralManager.connect(peripheral, options: nil)
//                }
//            }
//        }
//    }
//
//    func peripheral(_ peripheral: CBPeripheral, didUpdateNotificationStateFor characteristic: CBCharacteristic, error: Error?) {
//        if let error = error {
//            print("Error changing notification state: \(error.localizedDescription)")
//        } else {
//            print("Notification state updated for \(characteristic.uuid): \(characteristic.isNotifying)")
//        }
//    }
//    func centralManager(_ central: CBCentralManager, didDisconnectPeripheral peripheral: CBPeripheral, error: Error?) {
//        print("Peripheral disconnected, trying to reconnect")
//        centralManager.connect(peripheral, options: nil)
//
//       // EventViewModel.shared.sendBLEEnd()
//    }
//
//}

class BLEManager: NSObject, CBCentralManagerDelegate, CBPeripheralDelegate, ObservableObject {
    static let shared = BLEManager()
    var centralManager: CBCentralManager!
    var connectedPeripheral: CBPeripheral?
    let serviceUUID = CBUUID(string: "03d5d5c4-a86c-11ee-9d89-8f2089a49e7e")
    let audioCharacteristicUUID = CBUUID(string: "b189a505-a86c-11ee-a5fb-8f2089a49e7e")
    private var frameSequencer: FrameSequencer?
    private let socketManager = SocketManager.shared
    
    override init() {
        super.init()
        centralManager = CBCentralManager(delegate: self, queue: nil, options: [CBCentralManagerOptionRestoreIdentifierKey: "com.untitledai.restorationKey"])
    }
    
    func centralManager(_ central: CBCentralManager, didConnect peripheral: CBPeripheral) {
        print("Connected to peripheral: name=\(peripheral.name ?? ""), UUID=\(peripheral.identifier)")
        peripheral.discoverServices([serviceUUID])
        frameSequencer = FrameSequencer()
    }
    
    func centralManagerDidUpdateState(_ central: CBCentralManager) {
        if central.state == .poweredOn {
            retrieveConnectedPeripherals()
            scanForPeripherals()
        }
    }
    
    private func retrieveConnectedPeripherals() {
        let connectedPeripherals = centralManager.retrieveConnectedPeripherals(withServices: [serviceUUID])
        for peripheral in connectedPeripherals {
            connectedPeripheral = peripheral
            connectedPeripheral!.delegate = self
            centralManager.connect(connectedPeripheral!, options: nil)
        }
    }
    
    func scanForPeripherals() {
        print("Starting scan for peripherals")
        centralManager.scanForPeripherals(withServices: [serviceUUID], options: [CBCentralManagerScanOptionAllowDuplicatesKey: NSNumber(value: true)])
    }
    
    func centralManager(_ central: CBCentralManager, didDiscover peripheral: CBPeripheral, advertisementData: [String: Any], rssi RSSI: NSNumber) {
        let peripheralName = peripheral.name ?? "Unknown"
        let peripheralId = peripheral.identifier

        print("""
              Discovered Peripheral: \(peripheralName)
              Identifier: \(peripheralId)
              RSSI: \(RSSI)
              """)
        
        if connectedPeripheral == nil {
            connectedPeripheral = peripheral
            connectedPeripheral!.delegate = self
            centralManager.connect(connectedPeripheral!, options: nil)
        } else if connectedPeripheral?.identifier == peripheral.identifier, connectedPeripheral?.state != .connected {
            centralManager.connect(connectedPeripheral!, options: nil)
        }
        centralManager.stopScan()
    }
    
    func peripheral(_ peripheral: CBPeripheral, didDiscoverServices error: Error?) {
        print("Discovered services")
        guard let services = peripheral.services else { return }
        
        for service in services {
            peripheral.discoverCharacteristics(nil, for: service)
        }
    }
    
    func peripheral(_ peripheral: CBPeripheral, didDiscoverCharacteristicsFor service: CBService, error: Error?) {
        print("Discovered characteristics")
        print(service.characteristics)
        guard let characteristics = service.characteristics else { return }
        for characteristic in characteristics {
            if characteristic.uuid.isEqual(audioCharacteristicUUID) {
                if characteristic.properties.contains(.notify) {
                    print("Subscribing to characteristic \(characteristic.uuid)")
                    peripheral.setNotifyValue(true, for: characteristic)
                } else {
                    print("Characteristic does not support notifications")
                }
            }
        }
    }
    
    func peripheral(_ peripheral: CBPeripheral, didUpdateValueFor characteristic: CBCharacteristic, error: Error?) {
        if let error = error {
            print("Error updating value: \(error.localizedDescription)")
            return
        }
        
        guard let value = characteristic.value else {
            print("No value received")
            return
        }
        
        if characteristic.uuid.isEqual(audioCharacteristicUUID) {
            if let  completeFrames = frameSequencer?.add(packet: value) {
                for frame in completeFrames {
                    socketManager.sendAudioData(frame) // if streaming enabled
                    // TODO: append to writer
                }
            }
        }
    }
    
    func centralManager(_ central: CBCentralManager, willRestoreState dict: [String: Any]) {
        if let restoredPeripherals = dict[CBCentralManagerRestoredStatePeripheralsKey] as? [CBPeripheral] {
            for peripheral in restoredPeripherals {
                connectedPeripheral = peripheral
                connectedPeripheral!.delegate = self
                
                if peripheral.state == .connected {
                    peripheral.discoverServices([serviceUUID])
                } else if peripheral.state == .disconnected {
                    centralManager.connect(peripheral, options: nil)
                }
            }
        }
    }
    
    func peripheral(_ peripheral: CBPeripheral, didUpdateNotificationStateFor characteristic: CBCharacteristic, error: Error?) {
        if let error = error {
            print("Error changing notification state: \(error.localizedDescription)")
        } else {
            print("Notification state updated for \(characteristic.uuid): \(characteristic.isNotifying)")
        }
    }
    
    func centralManager(_ central: CBCentralManager, didDisconnectPeripheral peripheral: CBPeripheral, error: Error?) {
        print("Peripheral disconnected, trying to reconnect")
        socketManager.finishAudio()
        centralManager.connect(peripheral, options: nil)
    }
  
}
