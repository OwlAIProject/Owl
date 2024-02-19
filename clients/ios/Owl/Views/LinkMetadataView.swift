//
//  LinkMetadataView.swift
//  UntitledAI
//
//  Created by ethan on 2/17/24.
//

import SwiftUI
import LinkPresentation

struct LPLinkViewRepresented: UIViewRepresentable {
    var metadata: LPLinkMetadata
    
    func makeUIView(context: Context) -> LPLinkView {
        return LPLinkView(metadata: metadata)
    }
    
    func updateUIView(_ uiView: LPLinkView, context: Context) {
        
    }
}

struct LinkMetadataView : View {
    @StateObject var vm : LinkViewModel
    
    var body: some View {
        if let metadata = vm.metadata {
            LPLinkViewRepresented(metadata: metadata)
        } else {
            EmptyView()
        }
    }
}

class LinkViewModel : ObservableObject {
    let metadataProvider = LPMetadataProvider()
    
    @Published var metadata: LPLinkMetadata?
    
    init(link : String) {
        guard let url = URL(string: link) else {
            return
        }
        metadataProvider.startFetchingMetadata(for: url) { (metadata, error) in
            guard error == nil else {
                assertionFailure("Error")
                return
            }
            DispatchQueue.main.async {
                self.metadata = metadata
            }
        }
    }
}
