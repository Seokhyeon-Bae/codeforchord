import AVFoundation
import SwiftUI
import UniformTypeIdentifiers

private extension View {
    func cfcToolbar(showSettings: Binding<Bool>) -> some View {
        toolbar {
            ToolbarItem(placement: .topBarTrailing) {
                Button {
                    showSettings.wrappedValue = true
                } label: {
                    Image(systemName: "gearshape.fill")
                }
            }
        }
    }
}

// MARK: - Upload

struct UploadTabView: View {
    @Binding var showSettings: Bool
    @EnvironmentObject private var appState: AppState
    @State private var showImporter = false

    private let importTypes: [UTType] = [.audio, .mp3, .mpeg4Audio, .wav, .aiff, .movie]

    var body: some View {
        List {
            Section {
                Button {
                    showImporter = true
                } label: {
                    Label("Choose audio file", systemImage: "folder.fill")
                }
                if appState.hasAudio {
                    LabeledContent("File", value: appState.audioFileName)
                    Button("Clear file", role: .destructive) {
                        appState.clearAudio()
                    }
                }
            } header: {
                Text("Import")
            } footer: {
                Text("Supported formats match the backend (e.g. WAV, MP3, M4A).")
            }
        }
        .navigationTitle("Upload")
        .cfcToolbar(showSettings: $showSettings)
        .fileImporter(
            isPresented: $showImporter,
            allowedContentTypes: importTypes,
            allowsMultipleSelection: false
        ) { result in
            switch result {
            case .success(let urls):
                guard let url = urls.first else { return }
                let got = url.startAccessingSecurityScopedResource()
                defer { if got { url.stopAccessingSecurityScopedResource() } }
                let dest = FileManager.default.temporaryDirectory.appendingPathComponent(url.lastPathComponent)
                do {
                    if FileManager.default.fileExists(atPath: dest.path) {
                        try FileManager.default.removeItem(at: dest)
                    }
                    try FileManager.default.copyItem(at: url, to: dest)
                    appState.setAudio(url: dest)
                } catch {
                    appState.errorMessage = error.localizedDescription
                }
            case .failure(let err):
                appState.errorMessage = err.localizedDescription
            }
        }
    }
}

// MARK: - Record

struct RecordTabView: View {
    @Binding var showSettings: Bool
    @EnvironmentObject private var appState: AppState
    @State private var recording = false
    @State private var recorder: AVAudioRecorder?
    @State private var recordURL: URL?

    var body: some View {
        List {
            Section {
                if recording {
                    Button("Stop & save", role: .destructive) {
                        stopRecording()
                    }
                    Text("Recording… speak or play near the microphone.")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                } else {
                    Button {
                        startRecording()
                    } label: {
                        Label("Start recording", systemImage: "record.circle")
                    }
                    if appState.hasAudio {
                        LabeledContent("Saved", value: appState.audioFileName)
                    }
                }
            } header: {
                Text("Microphone")
            } footer: {
                Text("Saves as M4A (AAC) in a temp file, then sends to the same APIs as upload.")
            }
        }
        .navigationTitle("Record")
        .cfcToolbar(showSettings: $showSettings)
    }

    private func startRecording() {
        AVAudioSession.sharedInstance().requestRecordPermission { allowed in
            guard allowed else {
                DispatchQueue.main.async {
                    appState.errorMessage = "Microphone permission denied. Enable it in Settings."
                }
                return
            }
            DispatchQueue.main.async {
                do {
                    let session = AVAudioSession.sharedInstance()
                    try session.setCategory(.playAndRecord, mode: .default)
                    try session.setActive(true)

                    let url = FileManager.default.temporaryDirectory
                        .appendingPathComponent("cfc-recording-\(UUID().uuidString).m4a")
                    let settings: [String: Any] = [
                        AVFormatIDKey: Int(kAudioFormatMPEG4AAC),
                        AVSampleRateKey: 44_100,
                        AVNumberOfChannelsKey: 1,
                        AVEncoderAudioQualityKey: AVAudioQuality.high.rawValue,
                    ]
                    let rec = try AVAudioRecorder(url: url, settings: settings)
                    rec.prepareToRecord()
                    rec.record()
                    recorder = rec
                    recordURL = url
                    recording = true
                    appState.errorMessage = nil
                } catch {
                    appState.errorMessage = error.localizedDescription
                }
            }
        }
    }

    private func stopRecording() {
        recorder?.stop()
        recorder = nil
        recording = false
        try? AVAudioSession.sharedInstance().setActive(false)
        if let url = recordURL {
            appState.setAudio(url: url)
        }
        recordURL = nil
    }
}

// MARK: - Analysis

struct AnalysisTabView: View {
    @Binding var showSettings: Bool
    @EnvironmentObject private var appState: AppState

    var body: some View {
        List {
            if let err = appState.errorMessage {
                Section {
                    Text(err).foregroundStyle(.red)
                }
            }
            if let msg = appState.statusMessage {
                Section {
                    Text(msg).foregroundStyle(.green)
                }
            }

            Section("Track") {
                if appState.hasAudio {
                    LabeledContent("File", value: appState.audioFileName)
                } else {
                    Text("No audio — use Upload or Record.")
                        .foregroundStyle(.secondary)
                }
            }

            Section("Instrument") {
                Picker("Type", selection: $appState.instrument) {
                    Text("Piano").tag("piano")
                    Text("Guitar").tag("guitar")
                    Text("Vocal").tag("vocal")
                }
                .pickerStyle(.segmented)
            }

            Section("Metadata") {
                TextField("Title", text: $appState.title)
                Stepper("Tempo: \(appState.tempo) BPM", value: $appState.tempo, in: 40...220)
                Picker("Time signature", selection: $appState.timeSignature) {
                    Text("4/4").tag("4/4")
                    Text("3/4").tag("3/4")
                    Text("6/8").tag("6/8")
                    Text("2/4").tag("2/4")
                }
                if let ti = appState.tempoInfo {
                    LabeledContent("Detected tempo", value: "\(Int(ti.tempo.rounded())) BPM")
                }
                if let ts = appState.timeSignatureInfo {
                    LabeledContent("Detected meter", value: ts.timeSignature)
                }
            }

            Section("Run") {
                Button("Full analysis") {
                    Task { await appState.runFullAnalysis() }
                }
                .disabled(!appState.hasAudio || appState.isBusy)
                Button("Chords only") {
                    Task { await appState.runChordsOnly() }
                }
                .disabled(!appState.hasAudio || appState.isBusy)
            }

            if let chords = appState.chords {
                Section("Chords (\(chords.chords.count))") {
                    ForEach(chords.chords.prefix(40)) { c in
                        HStack {
                            Text(c.symbol).font(.headline)
                            Spacer()
                            Text(String(format: "%.1fs", c.timestamp))
                                .font(.caption)
                                .foregroundStyle(.secondary)
                        }
                    }
                    if chords.chords.count > 40 {
                        Text("…and \(chords.chords.count - 40) more")
                            .font(.caption)
                            .foregroundStyle(.secondary)
                    }
                }
            }

            if let notes = appState.notes, !notes.notes.isEmpty {
                Section("Notes (\(notes.notes.count))") {
                    Text("First \(min(5, notes.notes.count)) shown.")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                    ForEach(notes.notes.prefix(5)) { n in
                        Text("MIDI \(n.pitch) @ \(String(format: "%.2f", n.startTime))s")
                    }
                }
            }
        }
        .navigationTitle("Analysis")
        .cfcToolbar(showSettings: $showSettings)
    }
}

// MARK: - Sheet

struct SheetTabView: View {
    @Binding var showSettings: Bool
    @EnvironmentObject private var appState: AppState
    @State private var outputType = "lead_sheet"

    var body: some View {
        List {
            Section {
                Picker("Output", selection: $outputType) {
                    Text("Chords only").tag("chords_only")
                    Text("Lead sheet").tag("lead_sheet")
                    Text("Full score").tag("full_score")
                }
                VStack(alignment: .leading) {
                    Text("Rhythm correction: \(Int(appState.correctionStrength * 100))%")
                    Slider(value: $appState.correctionStrength, in: 0...1, step: 0.1)
                }
                Button("Generate sheet music") {
                    Task { await appState.generateSheet(outputType: outputType) }
                }
                .disabled(!appState.hasAudio || appState.isBusy)
            }

            if let content = appState.sheetContent, let name = appState.sheetFilename {
                Section("Result") {
                    Text("Generated \(content.count) characters of MusicXML.")
                        .font(.caption)
                    if let url = writeTempMusicXML(content: content, filename: name) {
                        ShareLink(item: url, message: Text("CodeForChord export")) {
                            Label("Share / save .musicxml", systemImage: "square.and.arrow.up")
                        }
                    }
                }
            }

            if let err = appState.errorMessage {
                Section {
                    Text(err).foregroundStyle(.red)
                }
            }
        }
        .navigationTitle("Sheet")
        .cfcToolbar(showSettings: $showSettings)
    }

    private func writeTempMusicXML(content: String, filename: String) -> URL? {
        let safe = filename.replacingOccurrences(of: "/", with: "-")
        let url = FileManager.default.temporaryDirectory.appendingPathComponent("\(safe).musicxml")
        do {
            try content.write(to: url, atomically: true, encoding: .utf8)
            return url
        } catch {
            return nil
        }
    }
}

// MARK: - Arrange

struct ArrangeTabView: View {
    @Binding var showSettings: Bool
    @EnvironmentObject private var appState: AppState
    @State private var melodyStyle = "simple"

    var body: some View {
        List {
            Section("Mode conversion (chords-only)") {
                if appState.isChordsOnlyAnalysis {
                    Text("Parallel major ↔ minor on the detected progression.")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                    Button("Major → Minor") {
                        Task { await appState.convertMode("minor") }
                    }
                    .disabled(appState.isBusy)
                    Button("Minor → Major") {
                        Task { await appState.convertMode("major") }
                    }
                    .disabled(appState.isBusy)
                } else {
                    Text("Run “Chords only” on the Analysis tab first (no note list).")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }
            }

            Section("Melody suggestion (chords-only)") {
                if appState.isChordsOnlyAnalysis {
                    Picker("Style", selection: $melodyStyle) {
                        Text("Simple").tag("simple")
                        Text("Arpeggiated").tag("arpeggiated")
                        Text("Scalar").tag("scalar")
                        Text("Rhythmic").tag("rhythmic")
                    }
                    Button("Generate melody (API)") {
                        Task { await appState.generateMelody(style: melodyStyle) }
                    }
                    .disabled(!appState.hasAudio || appState.isBusy)
                } else {
                    Text("Available only after “Chords only” analysis.")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }
            }

            if let msg = appState.statusMessage {
                Section { Text(msg).foregroundStyle(.green) }
            }
            if let err = appState.errorMessage {
                Section { Text(err).foregroundStyle(.red) }
            }
        }
        .navigationTitle("Arrange")
        .cfcToolbar(showSettings: $showSettings)
    }
}
