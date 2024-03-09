package com.owl.Owl

import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.lifecycle.viewmodel.compose.viewModel

@Composable
fun ConversationsScreen(viewModel: ConversationsViewModel = viewModel()) {
    val conversations = viewModel.conversations.collectAsState(initial = emptyList())

    LazyColumn(
        contentPadding = PaddingValues(horizontal = 16.dp, vertical = 8.dp)
    ) {
        items(conversations.value, key = { it.id }) { conversation ->
            ConversationItem(conversation = conversation)
        }
    }
}

@Composable
fun ConversationItem(conversation: Conversation) {
    Column(modifier = Modifier.padding(vertical = 8.dp)) {
        Text(
            text = "Start Time: ${conversation.startTime}",
            modifier = Modifier.padding(bottom = 4.dp)
        )
        Text(
            text = "State: ${conversation.state}",
            modifier = Modifier.padding(bottom = 4.dp)
        )
        Text(
            text = "Summary: ${conversation.shortSummary ?: conversation.summary ?: "No summary"}",
            maxLines = 2,
            overflow = TextOverflow.Ellipsis
        )
    }
}