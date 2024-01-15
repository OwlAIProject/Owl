//
//  FrameSequencer.swift
//
//  Created by Bart Trzynadlowski on 1/11/24.
//

//
// Header format for audio frame packets:
//
//          Bit
//   Byte    7  4 3  0
//          +----+----+
//    0     |xxxx|ffff|
//          +----+----+
//
//          +----+----+
//    1     |nnnn|ssss|
//          +----+----+
//
//  xxxx    Reserved
//  ffff    Inter-frame sequence number (complete frame)
//  nnnn    Number of BLE packets in this frame
//  ssss    Sequence number for this frame (intra-frame), [0,n)
//

import Foundation

class FrameSequencer {
    private var _packets: [Data] = []

    /// Add the next packet in the sequence and, if a complete frame has been received, return all
    /// packets in the frame. Drops out-of-sequence packets.
    /// - Parameter packet: An audio packet from the Xiao, with 2 byte header.
    /// - Returns: `nil` if a complete frame has not yet been received otherwise an array of all
    /// frame data (with header bytes stripped).
    func add(packet data: Data) -> [Data]? {
        // We expect intraframe seqno's of 0...n and the same interframe seqno for all
        let (interframeSeqno, numPackets, intraframeSeqno) = extractSequenceNumbers(from: data)

        if _packets.count > 0 {
            let (prevInterframeSeqno, prevNumPackets, prevIntraframeSeqno) = extractSequenceNumbers(from: _packets.last!)
            let expectedIntraframeSeqno = (prevIntraframeSeqno + 1) & 0xf
            if interframeSeqno == prevInterframeSeqno && numPackets == prevNumPackets && intraframeSeqno == expectedIntraframeSeqno {
                // New packet is next packet in sequence
                _packets.append(data)
                if intraframeSeqno == (numPackets - 1) {
                    // All packets received!
                    let packets = _packets
                    _packets.removeAll()
                    return packets.map { $0.subdata(in: 2..<$0.count) }
                }
                return nil
            } else {
                // New packet is not next packet in sequence, drop existing ones, then fall through
                // to "first packet" case
                _packets.removeAll()
            }
        }

        if _packets.count == 0 {
            // Special case: first packet received. Ensure it is first packet of frame and check
            // whether only one packet in frame.
            if intraframeSeqno == 0 {
                if numPackets == 1 {
                    return [ data.subdata(in: 2..<data.count) ]
                }
                _packets.append(data)
            }
        }

        return nil
    }

    private func extractSequenceNumbers(from data: Data) -> (Int, Int, Int) {
        let interframeSeqno = data[0] & 0xf
        let numPackets = data[1] >> 4
        let intraframeSeqno = data[1] & 0xf
        return (Int(interframeSeqno), Int(numPackets), Int(intraframeSeqno))
    }
}
