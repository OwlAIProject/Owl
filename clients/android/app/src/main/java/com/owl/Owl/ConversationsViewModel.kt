package com.owl.Owl

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

class ConversationsViewModel : ViewModel() {

    private val apiService = ApiServiceSingleton.apiService

    private val _conversations = MutableStateFlow<List<Conversation>>(emptyList())
    val conversations = _conversations.asStateFlow()

    init {
        fetchConversations()
    }

    fun fetchConversations() {
        viewModelScope.launch {
           _conversations.value = apiService.fetchConversations()
        }
    }
}