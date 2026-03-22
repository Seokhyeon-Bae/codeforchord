import Foundation

enum AppConfiguration {
    private static let storageKey = "cfc_api_base_url"

    /// Simulator default: Mac localhost. Physical device: set your computer's LAN IP (e.g. http://192.168.1.10:8000).
    static var apiBaseURL: String {
        let raw = UserDefaults.standard.string(forKey: storageKey) ?? ""
        let trimmed = raw.trimmingCharacters(in: .whitespacesAndNewlines)
        return trimmed.isEmpty ? "http://127.0.0.1:8000" : trimmed
    }

    static func setAPIBaseURL(_ value: String) {
        UserDefaults.standard.set(value, forKey: storageKey)
    }
}
