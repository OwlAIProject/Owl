package com.owl.Owl

import com.google.gson.annotations.SerializedName
import java.util.Date

data class ConversationsResponse(
    @SerializedName("conversations") val conversations: List<Conversation>
)

enum class ConversationState {
    @SerializedName("CAPTURING") CAPTURING,
    @SerializedName("PROCESSING") PROCESSING,
    @SerializedName("COMPLETED") COMPLETED,
    @SerializedName("FAILED_PROCESSING") FAILED_PROCESSING
}

data class SuggestedLink(
    @SerializedName("url") val url: String
)

data class Conversation(
    @SerializedName("id") val id: Int,
    @SerializedName("start_time") val startTime: String,
    @SerializedName("end_time") val endTime: String? = null,
    @SerializedName("conversation_uuid") val conversationUUID: String,
    @SerializedName("capture_segment_file") val captureFileSegment: CaptureFileSegment,
    @SerializedName("device_type") val deviceType: String,
    @SerializedName("summary") val summary: String? = null,
    @SerializedName("summarization_model") val summarizationModel: String? = null,
    @SerializedName("short_summary") val shortSummary: String? = null,
    @SerializedName("state") val state: ConversationState,
    @SerializedName("transcriptions") val transcriptions: List<Transcription>,
    @SerializedName("primary_location") val primaryLocation: Location? = null,
    @SerializedName("suggested_links") val suggestedLinks: List<SuggestedLink>? = null
)

data class CaptureFile(
    @SerializedName("id") val id: Int,
    @SerializedName("filepath") val filePath: String,
    @SerializedName("start_time") val startTime: String,
    @SerializedName("device_type") val deviceType: String
)

data class CaptureFileSegment(
    @SerializedName("id") val id: Int,
    @SerializedName("filepath") val filePath: String,
    @SerializedName("duration") val duration: Double? = null,
    @SerializedName("source_capture") val sourceCapture: CaptureFile
)

data class Transcription(
    @SerializedName("id") val id: Int,
    @SerializedName("model") val model: String,
    @SerializedName("realtime") val realtime: Boolean,
    @SerializedName("transcription_time") val transcriptionTime: Double,
    @SerializedName("utterances") val utterances: List<Utterance>
)

data class Utterance(
    @SerializedName("id") val id: Int,
    @SerializedName("start") val start: Double? = null,
    @SerializedName("end") val end: Double? = null,
    @SerializedName("text") val text: String? = null,
    @SerializedName("speaker") val speaker: String? = null
)

data class Word(
    @SerializedName("id") val id: Int,
    @SerializedName("word") val word: String,
    @SerializedName("start") val start: Double? = null,
    @SerializedName("end") val end: Double? = null,
    @SerializedName("score") val score: Double? = null,
    @SerializedName("speaker") val speaker: String? = null,
    @SerializedName("utterance_id") val utteranceId: Int? = null
)

data class Location(
    @SerializedName("id") val id: Int? = null,
    @SerializedName("latitude") val latitude: Double,
    @SerializedName("longitude") val longitude: Double,
    @SerializedName("address") val address: String? = null,
    @SerializedName("capture_uuid") val captureUUID: String? = null
)

data class Capture(
    @SerializedName("capture_uuid") val captureUUID: String,
    @SerializedName("device_name") val deviceName: String,
    @SerializedName("last_disconnect_time") var lastDisconnectTime: String? = null,
    @SerializedName("last_connect_time") var lastConnectTime: String? = null
)
