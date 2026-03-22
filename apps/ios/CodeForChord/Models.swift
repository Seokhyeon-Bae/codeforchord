import Foundation

// MARK: - Chords

struct ChordList: Codable, Equatable {
    var chords: [DetectedChord]
    var sourceFile: String?
    var duration: Double?
    var key: String?
}

struct DetectedChord: Codable, Identifiable, Equatable {
    var id: String { "\(symbol)-\(timestamp)" }
    let symbol: String
    let root: String
    let quality: String
    let timestamp: Double
    let duration: Double
    let bassNote: String?
    let confidence: Double?
}

// MARK: - Notes

struct NoteList: Codable, Equatable {
    var notes: [DetectedNote]
    var sourceFile: String?
    var duration: Double?
}

struct DetectedNote: Codable, Identifiable, Equatable {
    var id: String { "\(pitch)-\(startTime)" }
    let pitch: Int
    let startTime: Double
    let duration: Double
    let velocity: Int?
    let confidence: Double?
}

// MARK: - Full detection

struct FullDetectionResponse: Codable {
    let notes: NoteList?
    let chords: ChordList?
    let instrument: String?
    let sourceFile: String?
    let tempoInfo: TempoInfo?
    let timeSignatureInfo: TimeSignatureInfo?
}

struct TempoInfo: Codable, Equatable {
    let tempo: Double
    let tempoRange: [Double]?
    let isVariable: Bool?
    let confidence: Double?
}

struct TimeSignatureInfo: Codable, Equatable {
    let timeSignature: String
    let beatsPerMeasure: Int?
    let confidence: Double?
}

// MARK: - Sheet

struct GeneratedSheet: Codable {
    let content: String
    let format: String
    let outputType: String
    let metadata: SheetMetadata
    let filename: String
}

struct SheetMetadata: Codable {
    let title: String?
    let composer: String?
    let tempo: Int?
    let timeSignature: String?
    let keySignature: String?
    let instrument: String?
}

// MARK: - Errors

struct FastAPIErrorDetail: Codable {
    let detail: String
}
