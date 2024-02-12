export class FrameSequencer {
    constructor() {
        this.packets = [];
        this.expectedNumPackets = null;
        this.expectedIntraframeSeqno = null;
    }

    add(data) {
        const interframeSeqno = data.getUint8(0) & 0x0F;
        const numPackets = data.getUint8(1) >> 4;
        const intraframeSeqno = data.getUint8(1) & 0x0F;

        console.log(`Received packet: Interframe: ${interframeSeqno}, Num: ${numPackets}, Intraframe: ${intraframeSeqno}`);

        if (this.expectedIntraframeSeqno === null || this.expectedNumPackets === null) {
            this.expectedIntraframeSeqno = intraframeSeqno;
            this.expectedNumPackets = numPackets;
        }

        if (intraframeSeqno !== this.expectedIntraframeSeqno || numPackets !== this.expectedNumPackets) {
            console.log(`Packet out of sequence. Resetting...`);
            this.resetState();
            return null;
        }

        this.packets.push(data.buffer.slice(2)); // Add the current packet (minus header)
        if (intraframeSeqno === numPackets - 1) {
            const completeFrame = this.concatenateBuffers(this.packets);
            this.resetState();
            return completeFrame;
        }

        // Prepare for the next packet
        this.expectedIntraframeSeqno = (this.expectedIntraframeSeqno + 1) % 16;
        return null;
    }

    resetState() {
        this.packets = [];
        this.expectedNumPackets = null;
        this.expectedIntraframeSeqno = null;
    }

    extractSequenceNumbers(dataBuffer) {
        const data = new DataView(dataBuffer);
        const interframeSeqno = data.getUint8(0) & 0x0F;
        const numPackets = data.getUint8(1) >> 4;
        const intraframeSeqno = data.getUint8(1) & 0x0F;
        return [interframeSeqno, numPackets, intraframeSeqno];
    }

    concatenateBuffers(arrayBuffers) {
        let totalLength = arrayBuffers.reduce((acc, value) => acc + value.byteLength, 0);
        let result = new Uint8Array(totalLength);
        let length = 0;
        for (let arrayBuffer of arrayBuffers) {
            result.set(new Uint8Array(arrayBuffer), length);
            length += arrayBuffer.byteLength;
        }
        return result.buffer;
    }
}