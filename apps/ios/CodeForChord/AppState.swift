import Foundation
import SwiftUI

@MainActor
final class AppState: ObservableObject {
    @Published var audioURL: URL?
    @Published var audioFileName: String = ""
    @Published var isBusy = false
    @Published var statusMessage: String?
    @Published var errorMessage: String?

    @Published var chords: ChordList?
    @Published var notes: NoteList?
    @Published var tempoInfo: TempoInfo?
    @Published var timeSignatureInfo: TimeSignatureInfo?

    @Published var sheetContent: String?
    @Published var sheetFilename: String?

    @Published var instrument: String = "piano"
    @Published var tempo: Int = 120
    @Published var timeSignature: String = "4/4"
    @Published var title: String = "Untitled"
    @Published var correctionStrength: Double = 0.5

    private let api = APIService()

    var hasAudio: Bool { audioURL != nil }
    var isChordsOnlyAnalysis: Bool {
        chords != nil && (notes == nil || notes!.notes.isEmpty)
    }

    func setAudio(url: URL) {
        audioURL = url
        audioFileName = url.lastPathComponent
        clearAnalysis()
    }

    func clearAudio() {
        audioURL = nil
        audioFileName = ""
        clearAnalysis()
    }

    func clearAnalysis() {
        chords = nil
        notes = nil
        tempoInfo = nil
        timeSignatureInfo = nil
        sheetContent = nil
        sheetFilename = nil
        errorMessage = nil
        statusMessage = nil
    }

    func runFullAnalysis() async {
        guard let url = audioURL else {
            errorMessage = "Select or record audio first."
            return
        }
        isBusy = true
        errorMessage = nil
        statusMessage = nil
        defer { isBusy = false }
        do {
            let r = try await api.detectFull(fileURL: url, instrument: instrument)
            notes = r.notes
            chords = r.chords
            tempoInfo = r.tempoInfo
            timeSignatureInfo = r.timeSignatureInfo
            if let t = r.tempoInfo?.tempo {
                tempo = Int(t.rounded())
            }
            if let ts = r.timeSignatureInfo?.timeSignature {
                timeSignature = ts
            }
            statusMessage = "Full analysis complete."
        } catch {
            errorMessage = error.localizedDescription
        }
    }

    func runChordsOnly() async {
        guard let url = audioURL else {
            errorMessage = "Select or record audio first."
            return
        }
        isBusy = true
        errorMessage = nil
        statusMessage = nil
        defer { isBusy = false }
        do {
            notes = nil
            chords = try await api.detectChords(fileURL: url)
            tempoInfo = nil
            timeSignatureInfo = nil
            statusMessage = "Chords-only analysis complete."
        } catch {
            errorMessage = error.localizedDescription
        }
    }

    func generateSheet(outputType: String) async {
        guard let url = audioURL else {
            errorMessage = "Select or record audio first."
            return
        }
        isBusy = true
        errorMessage = nil
        defer { isBusy = false }
        do {
            let sheet = try await api.generateSheet(
                fileURL: url,
                outputType: outputType,
                title: title,
                tempo: tempo,
                timeSignature: timeSignature,
                instrument: instrument,
                correctionStrength: correctionStrength
            )
            sheetContent = sheet.content
            sheetFilename = sheet.filename
            statusMessage = "Sheet music generated."
        } catch {
            errorMessage = error.localizedDescription
        }
    }

    func convertMode(_ mode: String) async {
        guard let current = chords else {
            errorMessage = "Run Chords Only analysis first."
            return
        }
        isBusy = true
        errorMessage = nil
        defer { isBusy = false }
        do {
            let updated = try await api.convertModeChords(chords: current, targetMode: mode)
            chords = updated
            sheetContent = nil
            statusMessage = mode == "minor" ? "Converted toward minor." : "Converted toward major."
        } catch {
            errorMessage = error.localizedDescription
        }
    }

    func generateMelody(style: String) async {
        guard let url = audioURL else {
            errorMessage = "Select or record audio first."
            return
        }
        isBusy = true
        errorMessage = nil
        defer { isBusy = false }
        do {
            _ = try await api.generateMelody(fileURL: url, style: style, tempo: tempo)
            statusMessage = "Melody generated (check response for MIDI in API docs)."
        } catch {
            errorMessage = error.localizedDescription
        }
    }

    func testConnection() async -> String {
        do {
            let s = try await api.health()
            return "OK: \(s)"
        } catch {
            return error.localizedDescription
        }
    }
}
