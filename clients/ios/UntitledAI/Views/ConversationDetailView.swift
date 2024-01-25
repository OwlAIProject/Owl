//
//  ConversationDetailView.swift
//  UntitledAI
//
//  Created by ethan on 1/23/24.
//

import Foundation
import SwiftUI
import MapKit

struct ConversationDetailView: View {
    var conversation: Conversation
    
    var body: some View {
        ScrollView {
            VStack(alignment: .leading) {
                ForEach(conversation.transcriptions, id: \.id) { transcription in
                    MetadataView(transcription: transcription)
                }
                
                Divider().padding(.vertical)
                
                SummaryView(conversation: conversation)
                
                Divider().padding(.vertical)
                
                if let primaryLocation = conversation.primaryLocation {
                    // still ios 16 style for now
                    Map(coordinateRegion: .constant(MKCoordinateRegion(center: primaryLocation.coordinate, span: MKCoordinateSpan(latitudeDelta: 0.05, longitudeDelta: 0.05))), interactionModes: [], annotationItems: [primaryLocation]) { location in
                        MapMarker(coordinate: location.coordinate)
                    }
                    .frame(height: 200)
                    .cornerRadius(15)
                    
                    Divider().padding(.vertical)
                }
                
                ForEach(conversation.transcriptions.flatMap { $0.utterances }, id: \.id) { utterance in
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
            .padding()
        }
        .navigationBarTitle(Text(conversation.summary), displayMode: .inline)
        .background(Color(.systemBackground))
        .padding(.horizontal)
    }
}

struct SummaryView: View {
    var conversation: Conversation
    
    var body: some View {
        VStack(alignment: .leading, spacing: 10) {
            Text(conversation.summary)
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
    var transcription: Transcription
    
    var body: some View {
        VStack(alignment: .leading, spacing: 10) {
            Text(transcription.model)
                .frame(maxWidth: .infinity, alignment: .leading)
                .font(.subheadline)
                .fontWeight(.bold)
            
            Text("\(String(format: "%.2f seconds", transcription.duration))")
                .frame(maxWidth: .infinity, alignment: .leading)
                .font(.subheadline)
                .fontWeight(.bold)
            
            Text(transcription.sourceDevice)
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
