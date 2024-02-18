//
//  BLEManager.swift
//  Owl
//
//  Created by ethan on 1/15/24.
//

import Foundation
import CoreBluetooth

class BLEManager: NSObject, CBCentralManagerDelegate, CBPeripheralDelegate, ObservableObject {
    
    static let shared = BLEManager()
    
    @Published var connectedDeviceName: String?
    @Published var batteryLevel: Int? = nil
    @Published var isCharging: Bool? = nil
    var centralManager: CBCentralManager!
    var connectedPeripheral: CBPeripheral?
    let serviceUUID = CBUUID(string: AppConstants.bleServiceUUID)
    let audioCharacteristicUUID = CBUUID(string: AppConstants.bleAudioCharacteristicUUID)
    let batteryLevelCharacteristicUUID = CBUUID(string: AppConstants.batteryLevelCharacteristicUUID)
    let chargingStateCharacteristicUUID = CBUUID(string: AppConstants.chargingStateCharacteristicUUID)
    private var frameSequencer: FrameSequencer?
    private let socketManager = SocketManager.shared
    
    override init() {
        super.init()
        centralManager = CBCentralManager(delegate: self, queue: nil, options: [CBCentralManagerOptionRestoreIdentifierKey: "com.owl.restorationKey"])
    }
    
    func centralManager(_ central: CBCentralManager, didConnect peripheral: CBPeripheral) {
        print("Connected to peripheral: name=\(peripheral.name ?? ""), UUID=\(peripheral.identifier)")
        DispatchQueue.main.async {
            self.connectedDeviceName = peripheral.name
        }
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
        guard let characteristics = service.characteristics else { return }
        
        for characteristic in characteristics {
            print(characteristic)
            switch characteristic.uuid {
            case audioCharacteristicUUID:
                if characteristic.properties.contains(.notify) {
                    peripheral.setNotifyValue(true, for: characteristic)
                }
            case batteryLevelCharacteristicUUID, chargingStateCharacteristicUUID:
                if characteristic.properties.contains(.notify) {
                    peripheral.setNotifyValue(true, for: characteristic)
                }
            default:
                print("Found an unrecognized characteristic: \(characteristic.uuid)")
            }
        }
    }

    func peripheral(_ peripheral: CBPeripheral, didUpdateValueFor characteristic: CBCharacteristic, error: Error?) {
        if let error = error {
            print("Error updating value: \(error.localizedDescription)")
            return
        }
        
        guard let value = characteristic.value else {
            print("No value received for characteristic: \(characteristic.uuid)")
            return
        }
        
        switch characteristic.uuid {
        case audioCharacteristicUUID:
            let capture = CaptureManager.shared.currentCapture ?? CaptureManager.shared.createCapture(deviceName: peripheral.name ?? "Unknown")
            CaptureManager.shared.reportConnect()
             
            if let completeFrames = frameSequencer?.add(packet: value) {
                for frame in completeFrames {
                    socketManager.sendAudioData(frame, capture: capture)
                    // TODO: append to writer
                }
            }
        case batteryLevelCharacteristicUUID:
            if let level = value.first {
                DispatchQueue.main.async {
                    self.batteryLevel = Int(level)
                }
            }
        case chargingStateCharacteristicUUID:
            if let state = value.first {
                DispatchQueue.main.async {
                    self.isCharging = state != 0
                }
            }
        default:
            print("Received update from unrecognized characteristic: \(characteristic.uuid)")
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
        if peripheral == connectedPeripheral {
            DispatchQueue.main.async {
                self.connectedDeviceName = nil
            }
        }
        CaptureManager.shared.reportDisconnect()
        centralManager.connect(peripheral, options: nil)
    }
  
}
