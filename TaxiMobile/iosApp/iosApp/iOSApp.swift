import SwiftUI
import UIKit
import UserNotifications
import FirebaseCore
import FirebaseMessaging
import Shared

final class TaxiMobileAppDelegate: NSObject, UIApplicationDelegate, UNUserNotificationCenterDelegate, MessagingDelegate {
    func application(
        _ application: UIApplication,
        didFinishLaunchingWithOptions launchOptions: [UIApplication.LaunchOptionsKey: Any]? = nil
    ) -> Bool {
        guard Bundle.main.path(forResource: "GoogleService-Info", ofType: "plist") != nil else {
            return true
        }
        FirebaseApp.configure()
        Messaging.messaging().delegate = self
        UNUserNotificationCenter.current().delegate = self
        UNUserNotificationCenter.current().requestAuthorization(options: [.alert, .badge, .sound]) { _, _ in
            // APNs registration is also required for background data refresh.
            // Alert permission controls presentation, not authoritative sync.
            DispatchQueue.main.async { application.registerForRemoteNotifications() }
        }
        return true
    }

    func application(_ application: UIApplication, didRegisterForRemoteNotificationsWithDeviceToken deviceToken: Data) {
        Messaging.messaging().apnsToken = deviceToken
    }

    func messaging(_ messaging: Messaging, didReceiveRegistration installationId: String?) {
        guard let installationId, !installationId.isEmpty else { return }
        IosPushRegistration.shared.submit(registrationId: installationId)
    }

    func application(
        _ application: UIApplication,
        didReceiveRemoteNotification userInfo: [AnyHashable: Any],
        fetchCompletionHandler completionHandler: @escaping (UIBackgroundFetchResult) -> Void
    ) {
        let accepted = PushRefreshSignals.shared.submit(
            eventType: userInfo["type"] as? String,
            resourceId: userInfo["resource_id"] as? String
        )
        completionHandler(accepted ? .newData : .noData)
    }
}

@main
struct iOSApp: App {
    @UIApplicationDelegateAdaptor(TaxiMobileAppDelegate.self) private var appDelegate

    var body: some Scene {
        WindowGroup {
            ContentView()
        }
    }
}
