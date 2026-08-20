import UIKit
import SwiftUI
import Shared

struct ComposeView: UIViewControllerRepresentable {
    let apiBaseUrl: String
    let mapStyleUrl: String
    let appRole: AppRole
    let showManualCoordinateEntry: Bool

    func makeUIViewController(context: Self.Context) -> UIViewController {
        MainViewControllerKt.MainViewController(
            apiBaseUrl: apiBaseUrl,
            mapStyleUrl: mapStyleUrl,
            appRole: appRole,
            showManualCoordinateEntry: showManualCoordinateEntry
        )
    }

    func updateUIViewController(_ uiViewController: UIViewController, context: Self.Context) {}
}

struct ContentView: View {
    private let apiBaseUrl: String
    private let mapStyleUrl: String
    private let appRole: AppRole

    init(bundle: Bundle = .main) {
        apiBaseUrl = bundle.object(forInfoDictionaryKey: "TaxiMobileApiBaseUrl") as? String
            ?? "https://api.taximobile.invalid"
        mapStyleUrl = bundle.object(forInfoDictionaryKey: "TaxiMobileMapStyleUrl") as? String
            ?? "https://maps.taximobile.invalid/style.json"
        appRole = (bundle.object(forInfoDictionaryKey: "TaxiMobileAppRole") as? String) == "DRIVER"
            ? .driver
            : .passenger
    }

    var body: some View {
        ComposeView(
            apiBaseUrl: apiBaseUrl,
            mapStyleUrl: mapStyleUrl,
            appRole: appRole,
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
