# Always-on Perceptive AI


##  Requirements

- ffmpeg
- ollama (if using local llm)


## Source Code Tour

To help orient newcomers to the code base, we will trace the complete path that data takes through the system, from speech to displayed summary.

### Streaming Bluetooth Device Example: Xiao ESP32S3 Sense

Bluetooth-based devices, like the Xiao ESP32S3 Sense board in this example, connect to the iOS client application (`clients/ios`) and communicate with it continuously.

1. Audio is continuously picked up by the Sense board's microphone at 16 KHz and encoded to AAC. This reduces packets to a third of their original size, which is important because transmission consumes the most power. Packets are broadcast via BLE as fast as they are recorded in the board firmware's `loop()` function found in `clients/xiao-esp32s3-sense/firmware/src/main.cpp`.

2. Packets enter the iOS app in `peripheral(_:,didUpdateValueFor:,error:)` in `clients/ios/UntitledAI/Services/BLEManager.swift`. The iOS app passes complete frames to the server via a socket. *Frame* here refers to an AAC frame and there is a sequence numbering mechanism used to detect dropped BLE packets. AAC frames are independent, allowing us to drop incomplete frames that would cause downstream transcription models to choke.

3. Frames enter the server socket in `on_audio_data()` in `untitledai/server/capture_socket.py`. The `CaptureSocketApp` object is created with the FastAPI server in `main.py`. The capture session's UUID is used to look up the appropriate `StreamingCaptureHandler` and the data is forwarded there.

4. In `untitledai/server/streaming_capture_handler.py`, the audio data is appended to a file on disk and then passed along to a transcription service for real-time transcription and conversation endpoint detection. The `CaptureFile` object describes the location to which the entire capture is written. There is also a `CaptureSegmentFile`, which stores audio for the current conversation only. You can think of these as "children" of the parent capture file. A new one is created each time a conversation endpoint is detected.

5. The transcription service uses a streaming transcription model (Deepgram at the time of this writing, with a local option planned) that delivers utterances to `handle_utterance()`. This in turn passes the utterance, which includes timestamps, to the endpointing service. When the endpointing service determines a conversation has ended, `on_endpoint()` is invoked. The completed conversation segment file can be transcribed more thoroughly and summarized. A task is created and dispatched to the server's async background processing queue, which is processed continuously in `main.py` (`process_queue()`). The task, still in `streaming_capture_handler.py`, simply calls `process_conversation_from_audio()` on `ConversationService`, an instance of which is created as part of the server app's shared state (`AppState`).

6. `ConversationService` in `untitledai/services/conversation/conversation_service.py` transcribes the conversation audio using a non-streaming model, creates summaries, and associates a location with the conversation based on location data sent to the server from the iOS app. All this is committed to a local database as well as to the local capture directory in the form of JSON files for easy inspection. Finally, a notification is sent via `send_notification()` on a `NotificationService` instance (defined in `untitled/services/notification/notification_service.py`). This uses the socket connection to push the newly-created conversation to the iOS app.

7. Back in the iOS app: `ConversationsViewModel` in `clients/ios/UntitledAI/ViewModels/ConversationsViewModel.swift` subscribes to conversation messages and updates a published property whenever they arrive. The view model object is instantiated in `ContentView`, the top-level SwiftUI view, and handed to `ConversationsView`.

8. `ConversationsView` observes the view model and updates a list view whenever it changes, thereby displaying conversations to the user.

That sums up the end-to-end process, which begins in a capture device client, transits through the server, and ends at the iOS client.

### Chunked and Spooled Audio Example: Apple Watch

The server also supports non-real time syncing of capture data in chunks, which uses a different server route than the real-time streaming case. These can be uploaded long after a capture session has finished. Apple Watch has support for both streaming and spooling with opportunistic chunked uploads.

1. In the Watch app's `ContentView` (`clients/ios/UntitledAI Watch App/Views/ContentView.swift`), tapping the record button starts a capture session using the `CaptureManager` singleton object.

2. `CaptureManager` (`clients/ios/UntitledAI Watch App/Services/CaptureManager.swift`) starts recording by setting up an `AVAudioSession` and installing a tap to receive audio samples in `startAudioEngine()`. The tap downsamples to 16 KHz and passes the audio to an `AudioFileWriter` instance, which writes to disk. Even entry level Watch models have 32GB of disk space!

3. `AudioFileWriter` (`clients/ios/Shared/Files/AudioFileWriter.swift`) writes multiple sequential files named with the capture timestamp and UUID plus a sequential chunk number. After some time (e.g., 30 seconds), the current chunk is completed and the next file is created. Files contain raw PCM data and are equivalent to a header-less wave file.

4. Meanwhile, the Watch app runs an asynchronous task (see `clients/ios/Shared/FileUploadTask.swift`), spawned when the app launches, monitoring for files to upload. Files are uploaded sequentially via a POST to the server and deleted when this succeeds. Once all current files are uploaded, a special empty sentinel file is checked to determine whether the capture is actually finished and a processing request is sent to the server. The details of this process are explained in comment blocks in `FileUploadTask.swift`. Because files are stored on disk, they can be transferred while the recording is in progress or even hours or days later. Uploading can be disabled altogether via a setting in the app.

5. On the server, the `/capture/upload_chunk` route receives files. Files with the same `capture_uuid` are simply appended sequentially in the order they arrive. This happens in `untitledai/server/routes/capture.py`.

6. Each chunk of data is handed off to a background task, `ProcessAudioChunkTask`, processed asynchronously (`process_queue()` in `untitledai/server/main.py`). This task runs conversation detection incrementally to find conversation beginning and end timestamps. This process differs from the streaming version, although we hope to unify them somehow. A voice activity detector (VAD) is used to look for long stretches of silence to segment conversations, which is a naive and unreliable heuristic. Once conversations are identified, they are extracted into their own files and then sent off for processing using `process_conversation_from_audio()` on `ConversationService`. From this point onwards, the flow is the same as for the streaming case described above. It is important to note that conversations are detected as soon as possible by inspecting chunks.

7. Lastly, if the capture session ends and the `/process_capture` route is used, a final `ProcessAudioChunkTask` is submitted to finalize any remaining conversation that may have been ongoing in the final chunk.

Chunked uploads enter the server differently than streaming audio, use a different conversation endpointing method, but then follow the same path back to the iOS app.

## Capture Storage

Captures are stored in the directory specified by the `capture_dir` key in the YAML configuration file. They are organized by date and capture
device to make manual inspection easy. When conversations are detected within a capture, they are extracted into a subdirectory named after the capture file. The subdirectory will contain conversation audio files as well as transcripts and summaries in JSON form. Conversation detection may sometimes be incorrect; conversations that are too short or contain no dialog at all are not summarized and the corresponding JSON files will be absent.

| ![Capture sessions from February 6, 2024](docs/images/capture_storage/captures_today.png) | 
|:--:| 
| *Apple Watch captures recorded on February 6, 2024, with subdirectories for conversations.* |


| ![Conversations](docs/images/capture_storage/conversations.png) | 
|:--:| 
| *Conversations extracted from a particular capture.* |