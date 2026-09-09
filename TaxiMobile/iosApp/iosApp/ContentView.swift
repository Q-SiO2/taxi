import UIKit
import SwiftUI
import UniformTypeIdentifiers
import Shared

struct ComposeView: UIViewControllerRepresentable {
    let apiBaseUrl: String
    let mapStyleUrl: String
    let appRole: AppRole
    let appVersion: String
    let appBuild: String
    let showManualCoordinateEntry: Bool

    func makeCoordinator() -> DocumentPickerCoordinator {
        DocumentPickerCoordinator()
    }

    func makeUIViewController(context: Self.Context) -> UIViewController {
        let controller = MainViewControllerKt.MainViewController(
            apiBaseUrl: apiBaseUrl,
            mapStyleUrl: mapStyleUrl,
            appRole: appRole,
            appVersion: appVersion,
            appBuild: appBuild,
            showManualCoordinateEntry: showManualCoordinateEntry,
            requestDriverDocument: { completion in
                context.coordinator.present(completion: completion)
            }
        )
        context.coordinator.presenter = controller
        return controller
    }

    func updateUIViewController(_ uiViewController: UIViewController, context: Self.Context) {}
}

final class DocumentPickerCoordinator: NSObject, UIDocumentPickerDelegate {
    weak var presenter: UIViewController?
    private var completion: ((String?, String?, String?) -> Void)?

    func present(completion: @escaping (String?, String?, String?) -> Void) {
        guard self.completion == nil, let presenter else {
            completion(nil, nil, nil)
            return
        }
        self.completion = completion
        let picker = UIDocumentPickerViewController(
            forOpeningContentTypes: [.pdf, .jpeg, .png],
            asCopy: true
        )
        picker.delegate = self
        picker.allowsMultipleSelection = false
        presenter.present(picker, animated: true)
    }

    func documentPickerWasCancelled(_ controller: UIDocumentPickerViewController) {
        finish(fileName: nil, mediaType: nil, base64Content: nil)
    }

    func documentPicker(
        _ controller: UIDocumentPickerViewController,
        didPickDocumentsAt urls: [URL]
    ) {
        guard let url = urls.first else {
            finish(fileName: nil, mediaType: nil, base64Content: nil)
            return
        }
        let accessed = url.startAccessingSecurityScopedResource()
        defer {
            if accessed { url.stopAccessingSecurityScopedResource() }
        }
        do {
            let values = try url.resourceValues(forKeys: [.fileSizeKey, .contentTypeKey])
            guard let fileSize = values.fileSize, fileSize > 0, fileSize <= 10 * 1024 * 1024 else {
                throw DocumentPickerError.invalidSize
            }
            guard let contentType = values.contentType else {
                throw DocumentPickerError.invalidType
            }
            let mediaType: String
            if contentType.conforms(to: .pdf) {
                mediaType = "application/pdf"
            } else if contentType.conforms(to: .jpeg) {
                mediaType = "image/jpeg"
            } else if contentType.conforms(to: .png) {
                mediaType = "image/png"
            } else {
                throw DocumentPickerError.invalidType
            }
            let data = try Data(contentsOf: url, options: [.mappedIfSafe])
            guard !data.isEmpty, data.count <= 10 * 1024 * 1024 else {
                throw DocumentPickerError.invalidSize
            }
            finish(
                fileName: url.lastPathComponent,
                mediaType: mediaType,
                base64Content: data.base64EncodedString()
            )
        } catch {
            finish(fileName: nil, mediaType: nil, base64Content: nil)
            presentInvalidDocumentAlert()
        }
    }

    private func finish(fileName: String?, mediaType: String?, base64Content: String?) {
        let callback = completion
        completion = nil
        callback?(fileName, mediaType, base64Content)
    }

    private func presentInvalidDocumentAlert() {
        let alert = UIAlertController(
            title: "Document not accepted",
            message: "Choose one PDF, JPEG, or PNG file no larger than 10 MB.",
            preferredStyle: .alert
        )
        alert.addAction(UIAlertAction(title: "OK", style: .default))
        presenter?.present(alert, animated: true)
    }
}

private enum DocumentPickerError: Error {
    case invalidSize
    case invalidType
}

struct ContentView: View {
    private let apiBaseUrl: String
    private let mapStyleUrl: String
    private let appRole: AppRole
    private let appVersion: String
    private let appBuild: String

    init(bundle: Bundle = .main) {
        apiBaseUrl = bundle.object(forInfoDictionaryKey: "TaxiMobileApiBaseUrl") as? String
            ?? "https://api.taximobile.invalid"
        mapStyleUrl = bundle.object(forInfoDictionaryKey: "TaxiMobileMapStyleUrl") as? String
            ?? "https://maps.taximobile.invalid/style.json"
        appRole = (bundle.object(forInfoDictionaryKey: "TaxiMobileAppRole") as? String) == "DRIVER"
            ? .driver
            : .passenger
        appVersion = bundle.object(forInfoDictionaryKey: "CFBundleShortVersionString") as? String
            ?? "1.0.0"
        appBuild = bundle.object(forInfoDictionaryKey: "CFBundleVersion") as? String
            ?? "1"
    }

    var body: some View {
        ComposeView(
            apiBaseUrl: apiBaseUrl,
            mapStyleUrl: mapStyleUrl,
            appRole: appRole,
            appVersion: appVersion,
            appBuild: appBuild,
            showManualCoordinateEntry: isDebugBuild
        )
            .ignoresSafeArea()
    }
}

private var isDebugBuild: Bool {
#if DEBUG
    true
#else
    false
#endif
}
