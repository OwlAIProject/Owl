//
//  LinkMetadataView.swift
//  UntitledAI
//
//  Created by ethan on 2/17/24.
//

import Combine
import LinkPresentation
import SwiftUI
import UniformTypeIdentifiers

struct LinkPreviewData: Hashable {
    var originalURL: URL
    var title: String
    var image: NSItemProvider?
}

final class LinkExtractionService {
    static let `default` = LinkExtractionService()

    func fetchLinkPreview(_ url: URL) async throws -> LinkPreviewData {
        return try await withCheckedThrowingContinuation { continuation in
            let metadataProvider = LPMetadataProvider()
            DispatchQueue.main.async {
                metadataProvider.startFetchingMetadata(for: url) { metadata, error in
                    if let error {
                        continuation.resume(throwing: error)
                        return
                    }
                    guard let metadata = metadata else {
                        continuation.resume(throwing: NSError(domain: "InvalidResponse", code: 0))
                        return
                    }

                    let linkPreviewData = LinkPreviewData(originalURL: url, title: metadata.title ?? "", image: metadata.imageProvider)
                    continuation.resume(returning: linkPreviewData)
                }
            }
        }
    }
}

final class LinkPreviewViewModel: ObservableObject {
    private var isRequestInProgress: Bool = false
    @Published private(set) var viewData: LinkPreviewData?

    let url: URL
    init(url: URL) {
        self.url = url
        isRequestInProgress = true

        Task(priority: .background) {
            do {
                let data = try await LinkExtractionService.default.fetchLinkPreview(self.url)
                DispatchQueue.main.async {
                    self.isRequestInProgress = false
                    self.viewData = data
                    self.objectWillChange.send()
                }
            } catch {
                print("Failed to fetch link preview.", error)
                DispatchQueue.main.async {
                    self.isRequestInProgress = false
                    self.objectWillChange.send()
                }
            }
        }
    }

    var isLoading: Bool {
        isRequestInProgress
    }

    var hasFailed: Bool {
        if !isRequestInProgress {
            return viewData == nil
        } else {
            return false
        }
    }
}

struct LinkMetadataView: View {
    @Environment(\.openURL) var openURL

    @ObservedObject var linkPreview: LinkPreviewViewModel

    @State private var image: UIImage?
    @State private var isDataLoaded: Bool = false

    var body: some View {
        VStack {
            ZStack {
                Color.gray.opacity(0.2)
                    .cornerRadius(8)
                    .frame(width: 300, height: 240)

                if isDataLoaded {
                    contentView
                        .transition(.opacity)
                } else {
                    ProgressView()
                }
            }
        }
        .frame(width: 300, height: 240)
        .onAppear {
            fetchData()
        }
        .onChange(of: linkPreview.viewData) { _ in
            fetchData()
        }
        .onTapGesture {
            openURL(linkPreview.url)
        }
    }

    @ViewBuilder
    private var contentView: some View {
        VStack(spacing: 8) {
            if let image = self.image {
                Image(uiImage: image)
                    .resizable()
                    .scaledToFit()
                    .frame(height: 140)
                    .padding(.horizontal)
            } else {
                Image(systemName: "photo")
                    .foregroundColor(.gray)
                    .frame(height: 140)
                    .padding(.horizontal)
            }

            Text(linkPreview.viewData?.title ?? "")
                .font(.headline)
                .frame(height: 44, alignment: .top)
                .lineLimit(2)
                .multilineTextAlignment(.leading)
                .padding(.horizontal)
                .frame(maxWidth: .infinity, alignment: .leading)

            if let host = linkPreview.url.host {
                Text(host)
                    .font(.caption)
                    .foregroundColor(.gray)
                    .lineLimit(1)
                    .multilineTextAlignment(.leading)
                    .padding([.horizontal, .bottom])
                    .frame(maxWidth: .infinity, alignment: .leading)
            }
        }
        .frame(width: 300)
    }

    private func fetchData() {
        guard let viewData = linkPreview.viewData else {
            isDataLoaded = false
            return
        }

        updateImage(for: viewData) { success in
            DispatchQueue.main.async {
                withAnimation {
                    self.isDataLoaded = success
                }
            }
        }
    }

    private func updateImage(for viewData: LinkPreviewData?, completion: @escaping (Bool) -> Void) {
        guard let imageProvider = viewData?.image else {
            completion(true)
            return
        }
        imageProvider.loadDataRepresentation(forTypeIdentifier: UTType.image.identifier) { data, _ in
            DispatchQueue.main.async {
                if let data = data, let uiImage = UIImage(data: data) {
                    self.image = uiImage
                    completion(true)
                } else {
                    completion(false)
                }
            }
        }
    }
}
