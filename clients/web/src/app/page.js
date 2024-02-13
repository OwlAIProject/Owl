'use client';
import React, { useEffect, useState } from 'react';
import Link from 'next/link';
import { useSocket } from './hooks/useSocket';
import CountUpTimer from './components/CountUpTimer';

const ConversationsList = () => {
  const [conversations, setConversations] = useState([]);

  useEffect(() => {
    const fetchConversations = async () => {
      try {
        const response = await fetch(`/api/conversations`, {
          cache: 'no-store'
        });
        if (!response.ok) {
          throw new Error('Failed to fetch conversations');
        }
        const data = await response.json();
        setConversations(data.conversations);
      } catch (error) {
        console.error(error);
      }
    };

    fetchConversations();
  }, []);

  const socket = useSocket();

  useEffect(() => {
    if (socket) {
      const handleNewConversation = (newConversation) => {
        setConversations((prevConversations) => [JSON.parse(newConversation), ...prevConversations]);
      };

      const handleUpdateConversation = (updatedConversationJson) => {
        const updatedConversation = JSON.parse(updatedConversationJson);
        setConversations((prevConversations) =>
          prevConversations.map((conversation) =>
            conversation.id === updatedConversation.id ? updatedConversation : conversation
          )
        );
      };

      const handleDeleteConversation = (deletedConversationJson) => {
        const deletedConversation = JSON.parse(deletedConversationJson);
        setConversations((prevConversations) =>
          prevConversations.filter((conversation) => conversation.id !== deletedConversation.id)
        );
      };

      socket.on('new_conversation', handleNewConversation);
      socket.on('update_conversation', handleUpdateConversation);
      socket.on('delete_conversation', handleDeleteConversation);

      return () => {
        socket.off('new_conversation', handleNewConversation);
        socket.off('update_conversation', handleUpdateConversation);
        socket.off('delete_conversation', handleDeleteConversation);
      };
    }
  }, [socket]);

  const getConversationStateStyle = (state) => {
    switch (state) {
      case 'CAPTURING':
        return 'bg-blue-500';
      case 'PROCESSING':
        return 'bg-yellow-500';
      case 'COMPLETED':
        return 'bg-green-500';
      case 'FAILED_PROCESSING':
        return 'bg-red-500';
      default:
        return 'bg-gray-500';
    }
  };

  return (
    <div className="min-h-screen bg-black py-10">
      <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
        <h1 className="text-3xl font-bold text-center mb-10 text-white">Conversations</h1>
        <div className="space-y-6">
          {conversations.map((conversation) => (
            <Link
              href={`/conversations/${conversation.id}`}
              key={conversation.id}
              className="block transform transition duration-300 ease-in-out hover:-translate-y-1 hover:shadow-xl"
              passHref
            >
              <div className="p-6 rounded-lg border border-gray-700 flex justify-between items-center space-x-4">
                <div className="flex-1 min-w-0">
                  <h5 className="text-xl sm:text-2xl font-bold tracking-tight text-white truncate">{conversation.short_summary}</h5>
                  <p className="font-normal text-gray-400 mt-2">{new Date(`${conversation.start_time}Z`).toLocaleString()}</p>
                </div>
                {conversation.state === 'CAPTURING' ? (
                  <div className="flex-shrink-0 ml-4">
                    <CountUpTimer startTime={conversation.start_time} />
                  </div>
                ) : (
                  <span className={`px-4 py-1 rounded-full text-white ml-4 flex-shrink-0 ${getConversationStateStyle(conversation.state)}`}>
                    {conversation.state.replace('FAILED_PROCESSING', 'FAILED')}
                  </span>
                )}
              </div>
            </Link>
          ))}
        </div>
      </div>
    </div>
  );
  
  
};

export default ConversationsList;
