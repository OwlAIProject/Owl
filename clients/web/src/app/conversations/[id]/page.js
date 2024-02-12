'use client';
import React, { useEffect, useState, useRef } from 'react';
import { useSocket } from '../../hooks/useSocket';

const ConversationDetail = ({ params }) => {
    const [conversation, setConversation] = useState(null);
    const [googleMapsApiKey, setGoogleMapsApiKey] = useState('');
    const socket = useSocket();
    const conversationRef = useRef(conversation);

    const fetchConversation = async (id) => {
        const response = await fetch(`/api/conversations/${id}`, { cache: 'no-store' });
        if (!response.ok) {
            throw new Error('Failed to fetch conversations');
        }
        const data = await response.json();
        return data;
    }

    const fetchGoogleMapsApiKey = async () => {
        const response = await fetch(`/api/tokens`, {
            cache: 'no-store'
        });
        if (!response.ok) {
            throw new Error('Failed to fetch API tokens');
        }
        const data = await response.json();
        return data.GOOGLE_MAPS_API_KEY;
    };

    useEffect(() => {
        conversationRef.current = conversation;
    }, [conversation]);

    useEffect(() => {
        const fetchData = async () => {
            try {
                const conversationData = await fetchConversation(params.id);
                setConversation(conversationData);
                const apiKey = await fetchGoogleMapsApiKey();
                setGoogleMapsApiKey(apiKey);
            } catch (error) {
                console.error(error);
            }
        };

        fetchData();
    }, [params.id]);
    useEffect(() => {
        if (socket) {
            console.log('Socket setup');
            const handleUpdate = (updatedConversationJson) => {
                const updatedConversation = JSON.parse(updatedConversationJson);

                if (updatedConversation.id == params.id) {
                    console.log('Setting conversation');
                    setConversation(updatedConversation);
                }
            };
            const handleNewUtterance = (newUtterance) => {
                console.log(newUtterance)

                if (newUtterance.conversation_uuid === conversationRef.current?.conversation_uuid) {
                    const utterance = JSON.parse(newUtterance.utterance);
                    console.log(utterance)
                    setConversation(currentConversation => {
                        if (currentConversation) {
                            const updatedConversation = {
                                ...currentConversation,
                                transcriptions: currentConversation.transcriptions.map(transcription => {
                                    return {
                                        ...transcription,
                                        utterances: [...transcription.utterances, utterance]
                                    };
                                })
                            };
                            return updatedConversation;
                        }
                        return currentConversation;
                    });
                }
            };

            socket.on('new_utterance', handleNewUtterance);
            socket.on('update_conversation', handleUpdate);

            return () => {
                socket.off('update_conversation', handleUpdate);
                socket.off('new_utterance', handleNewUtterance);
            };
        }
    }, [socket, params.id]);

    if (!conversation) return null;
    const transcriptToShow = conversation.state === 'COMPLETED' ?
        conversation.transcriptions.find(transcript => !transcript.realtime) :
        conversation.transcriptions.find(transcript => transcript.realtime);

    return (
        <div className="max-w-4xl mx-auto p-5">
            <h1 className="text-2xl font-bold mb-4">Conversation Detail</h1>

            <div className="bg-white shadow overflow-hidden sm:rounded-lg mb-6">
                <div className="px-4 py-5 sm:px-6">
                    <h2 className="text-lg leading-6 font-medium text-gray-900">Summary</h2>
                    <p className="mt-1 max-w-2xl text-sm text-gray-500">{conversation.short_summary}</p>
                </div>
                <div className="border-t border-gray-200">
                    <dl>
                        <div className="bg-gray-50 px-4 py-5 sm:grid sm:grid-cols-3 sm:gap-4 sm:px-6">
                            <dt className="text-sm font-medium text-gray-500">Start Time</dt>
                            <dd className="mt-1 text-sm text-gray-900 sm:mt-0 sm:col-span-2">{new Date(conversation.start_time).toLocaleString()}</dd>
                        </div>
                        <div className="bg-white px-4 py-5 sm:grid sm:grid-cols-3 sm:gap-4 sm:px-6">
                            <dt className="text-sm font-medium text-gray-500">Full Summary</dt>
                            <dd className="mt-1 text-sm text-gray-900 sm:mt-0 sm:col-span-2 whitespace-pre-line">{conversation.summary}</dd>
                        </div>
                    </dl>
                </div>
            </div>

            <div className="mb-6">
                <h2 className="text-xl font-bold mb-2">Transcription</h2>
                {transcriptToShow && (
                    <div className="mb-6">
                        <div key={transcriptToShow.id} className="bg-white shadow overflow-hidden sm:rounded-lg mb-4">
                            <div className="px-4 py-5 sm:px-6">
                                <p className="mt-1 max-w-2xl text-sm text-gray-500">Model: {transcriptToShow.model}</p>
                            </div>
                            <div className="border-t border-gray-200">
                                <ul className="divide-y divide-gray-200">
                                    {transcriptToShow.utterances.map((utterance) => (
                                        <li key={utterance.id} className="px-4 py-4 sm:px-6">
                                            <div className="flex items-center justify-between">
                                                <div className="text-sm font-medium text-gray-600">
                                                    {utterance.text} <span className="text-gray-400">- {utterance.speaker}</span>
                                                </div>
                                                <div className="ml-2 flex-shrink-0 flex">
                                                    {utterance.start && (
                                                        <span className="px-2 inline-flex text-xs leading-5 font-semibold rounded-full bg-green-100 text-green-800">
                                                            {utterance.start.toFixed(2)}s - {utterance.end.toFixed(2)}s
                                                        </span>
                                                    )}
                                                </div>
                                            </div>
                                        </li>
                                    ))}
                                </ul>
                            </div>
                        </div>
                    </div>
                )}
            </div>

            {conversation.primary_location && (
                <div className="mb-6">
                    <h2 className="text-xl font-bold mb-2">Location</h2>
                    <div className="bg-white shadow overflow-hidden sm:rounded-lg">
                        <div className="px-4 py-5 sm:px-6">
                            <h3 className="text-lg leading-6 font-medium text-gray-900">Primary Location</h3>
                            <p className="mt-1 max-w-2xl text-sm text-gray-500">{conversation.primary_location.address}</p>
                        </div>
                        {googleMapsApiKey ? (
                            <div className="px-4 py-5 sm:px-6">
                                <img
                                    src={`https://maps.googleapis.com/maps/api/staticmap?center=${conversation.primary_location.latitude},${conversation.primary_location.longitude}&zoom=15&size=600x300&markers=color:red%7C${conversation.primary_location.latitude},${conversation.primary_location.longitude}&key=${googleMapsApiKey}`}
                                    alt="Location Map"
                                    className="w-full object-cover"
                                />
                            </div>
                        ) : (
                            <div className="px-4 py-5 sm:px-6 bg-gray-50">
                                <p className="mt-1 max-w-2xl text-sm text-gray-500">Latitude: {conversation.primary_location.latitude}</p>
                                <p className="mt-1 max-w-2xl text-sm text-gray-500">Longitude: {conversation.primary_location.longitude}</p>
                            </div>
                        )}
                    </div>
                </div>
            )}
        </div>
    );
}

export default ConversationDetail;