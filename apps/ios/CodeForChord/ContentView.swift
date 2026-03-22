import SwiftUI

struct ContentView: View {
    @StateObject private var appState = AppState()
    @State private var showSettings = false

    var body: some View {
        TabView {
            NavigationStack {
                UploadTabView(showSettings: $showSettings)
            }
            .tabItem { Label("Upload", systemImage: "square.and.arrow.up") }

            NavigationStack {
                RecordTabView(showSettings: $showSettings)
            }
            .tabItem { Label("Record", systemImage: "mic.fill") }

            NavigationStack {
                AnalysisTabView(showSettings: $showSettings)
            }
            .tabItem { Label("Analysis", systemImage: "chart.bar.fill") }

            NavigationStack {
                SheetTabView(showSettings: $showSettings)
            }
            .tabItem { Label("Sheet", systemImage: "music.note") }

            NavigationStack {
                ArrangeTabView(showSettings: $showSettings)
            }
            .tabItem { Label("Arrange", systemImage: "slider.horizontal.3") }
        }
        .tint(Color(red: 0.83, green: 0.65, blue: 0.35))
        .environmentObject(appState)
        .preferredColorScheme(.dark)
        .sheet(isPresented: $showSettings) {
            SettingsView()
                .environmentObject(appState)
        }
        .overlay {
            if appState.isBusy {
                ZStack {
                    Color.black.opacity(0.35).ignoresSafeArea()
                    ProgressView("Working…")
                        .padding(24)
                        .background(.ultraThinMaterial, in: RoundedRectangle(cornerRadius: 16))
                }
            }
        }
    }
}

#Preview {
    ContentView()
}
