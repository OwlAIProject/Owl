package com.owl.Owl

object ApiServiceSingleton {
    val apiService: ConversationApiService by lazy {
        ConversationApiService()
    }
}