package com.owl.Owl

import com.google.gson.Gson
import com.google.gson.reflect.TypeToken
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import okhttp3.OkHttpClient
import okhttp3.Request

class ConversationApiService {

    private val client = OkHttpClient()
    private val gson = Gson()

    suspend fun fetchConversations(): List<Conversation> = withContext(Dispatchers.IO) {
        try {
            val request = Request.Builder()
                .url("${AppConstants.apiBaseURL}/conversations")
                .addHeader("Authorization", "Bearer ${AppConstants.clientToken}")
                .build()

            client.newCall(request).execute().use { response ->
                if (!response.isSuccessful) throw Exception("Server responded with code $response")

                val responseBody = response.body?.string() ?: throw Exception("Null Response Body")
                val conversationsResponse = gson.fromJson(responseBody, ConversationsResponse::class.java)
                conversationsResponse.conversations
            }
        } catch (e: Exception) {
            e.printStackTrace()
            emptyList<Conversation>()
        }
    }
}