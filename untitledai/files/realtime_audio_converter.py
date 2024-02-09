import asyncio

class RealtimeAudioConverter:
    def __init__(self, ffmpeg_command, chunk_size=512):
        self._ffmpeg_command = ffmpeg_command
        self._chunk_size = chunk_size
        self._process = None
        self._stdin = None
        self._stdout = None

    async def start(self):
        """Start the ffmpeg process with asyncio subprocess and prepare non-blocking streams."""
        self._process = await asyncio.create_subprocess_exec(
            *self._ffmpeg_command,
            stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.DEVNULL)
        self._stdin = self._process.stdin
        self._stdout = self._process.stdout

    async def feed_input_chunk(self, input_chunk):
        """Feed an audio data chunk to ffmpeg's stdin asynchronously."""
        if self._stdin:
            self._stdin.write(input_chunk)
            await self._stdin.drain()

    async def close_input(self):
        """Close ffmpeg's stdin to signal that no more data will be sent."""
        if self._stdin:
            self._stdin.close()
            await self._stdin.wait_closed()

    async def read_output_chunk(self):
        """Asynchronously read and return a chunk of converted audio from ffmpeg's stdout."""
        return await self._stdout.read(self._chunk_size) 

    async def cleanup(self):
        """Wait for the ffmpeg process to exit and perform cleanup."""
        await self._process.wait()
