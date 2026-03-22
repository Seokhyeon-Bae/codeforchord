import SwiftUI

struct SettingsView: View {
    @EnvironmentObject private var appState: AppState
    @Environment(\.dismiss) private var dismiss
    @State private var urlText: String = ""
    @State private var testResult: String?

    var body: some View {
        NavigationStack {
            Form {
                Section("Backend API") {
                    TextField("Base URL", text: $urlText)
                        .textInputAutocapitalization(.never)
                        .autocorrectionDisabled()
                        .keyboardType(.URL)
                    Text("Simulator: `http://127.0.0.1:8000`. Physical iPhone: your Mac’s LAN IP, e.g. `http://192.168.1.10:8000`.")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                    Button("Save") {
                        AppConfiguration.setAPIBaseURL(urlText)
                        testResult = nil
                    }
                    Button("Test connection (GET /health)") {
                        Task {
                            testResult = await appState.testConnection()
                        }
                    }
                    if let testResult {
                        Text(testResult)
                            .font(.caption)
                            .foregroundStyle(testResult.hasPrefix("OK") ? .green : .red)
                    }
                }
            }
            .navigationTitle("Settings")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .confirmationAction) {
                    Button("Done") { dismiss() }
                }
            }
            .onAppear {
                urlText = AppConfiguration.apiBaseURL
            }
        }
    }
}
