//
//  ConversationDetailView.swift
//  Owl
//
//  Created by ethan on 1/23/24.
//

import Foundation
import SwiftUI
import MapKit

struct ConversationDetailView: View {
    var conversation: Conversation
    
    var transcriptToShow: Transcription? {
        if conversation.state == .completed {
            return conversation.finalTranscript
        } else {
            return conversation.realtimeTranscript
        }
    }
    
    var body: some View {
        ScrollView {
            VStack(alignment: .leading) {
                if conversation.summary != nil {
                    SummaryView(conversation: conversation)

                    Divider().padding(.vertical)
                }
  
                if let primaryLocation = conversation.primaryLocation {
                    Map(coordinateRegion: .constant(MKCoordinateRegion(center: primaryLocation.coordinate, span: MKCoordinateSpan(latitudeDelta: 0.05, longitudeDelta: 0.05))), interactionModes: [], annotationItems: [primaryLocation]) { location in
                        MapMarker(coordinate: location.coordinate)
                    }
                    .frame(height: 200)
                    .cornerRadius(15)

                    Divider().padding(.vertical)
                }
                
                if let suggestedLinks = conversation.suggestedLinks, !suggestedLinks.isEmpty {
                    ScrollView(.horizontal, showsIndicators: false) {
                        HStack {
                            ForEach(suggestedLinks, id: \.url) { suggestedLink in
                                LinkMetadataView(linkPreview: LinkPreviewViewModel(url: URL(string: suggestedLink.url)!))
                            }
                        }
                    }
                    Divider().padding(.vertical)
                }
                
                if let transcription = transcriptToShow {
                    MetadataView(conversation: conversation, transcription: transcription)

                    Divider().padding(.vertical)
                    if !transcription.utterances.isEmpty {
                        ForEach(transcription.utterances, id: \.id) { utterance in
                            HStack {
                                Text("\(utterance.speaker ?? "Unknown"):")
                                    .fontWeight(.semibold)
                                    .foregroundColor(.blue)

                                Text(utterance.text ?? "")
                                    .foregroundColor(.secondary)
                            }
                            Divider()
                        }
                    }
                }
            }
            .padding()
        }
        .navigationBarTitle(Text(conversation.summary ?? "Conversation"), displayMode: .inline)
        .background(Color(.systemBackground))
        .padding(.horizontal)
    }
}

struct SummaryView: View {
    var conversation: Conversation
    
    var body: some View {
        VStack(alignment: .leading, spacing: 10) {
            Text(conversation.summary ?? "")
                .frame(maxWidth: .infinity, alignment: .leading)
                .font(.subheadline)
                .fontWeight(.bold)
                .multilineTextAlignment(.leading)
        }
        .frame(maxWidth: .infinity)
        .padding()
        .background(Color(.secondarySystemBackground))
        .cornerRadius(8)
        .shadow(radius: 2)
    }
}


struct MetadataView: View {
    var conversation: Conversation
    var transcription: Transcription
    
    var body: some View {
        VStack(alignment: .leading, spacing: 10) {
            Text(transcription.model)
                .frame(maxWidth: .infinity, alignment: .leading)
                .font(.subheadline)
                .fontWeight(.bold)
            
            Text(conversation.summarizationModel ?? "")
                .frame(maxWidth: .infinity, alignment: .leading)
                .font(.subheadline)
                .fontWeight(.bold)
            
            if let duration = conversation.captureFileSegment.duration {
                Text("\(String(format: "%.2f seconds", duration))")
                    .frame(maxWidth: .infinity, alignment: .leading)
                    .font(.subheadline)
                    .fontWeight(.bold)
            }
            
            Text(conversation.captureFileSegment.sourceCapture.deviceType)
                .frame(maxWidth: .infinity, alignment: .leading)
                .font(.subheadline)
                .fontWeight(.bold)
        }
        .frame(maxWidth: .infinity)
        .padding()
        .background(Color(.secondarySystemBackground))
        .cornerRadius(8)
        .shadow(radius: 2)
    }
}
