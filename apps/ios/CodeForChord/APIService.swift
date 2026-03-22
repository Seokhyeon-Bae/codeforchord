import Foundation

enum APIClientError: LocalizedError {
    case invalidBaseURL
    case badStatus(Int, String)
    case decoding(Error)

    var errorDescription: String? {
        switch self {
        case .invalidBaseURL: return "Invalid API base URL"
        case .badStatus(let code, let msg): return "HTTP \(code): \(msg)"
        case .decoding(let e): return "Decode error: \(e.localizedDescription)"
        }
    }
}

final class APIService {
    private let session: URLSession

    init(session: URLSession = .shared) {
        self.session = session
    }

    private func decoder() -> JSONDecoder {
        let d = JSONDecoder()
        d.keyDecodingStrategy = .convertFromSnakeCase
        return d
    }

    private func baseURL() throws -> URL {
        let s = AppConfiguration.apiBaseURL.trimmingCharacters(in: .whitespacesAndNewlines)
        guard let url = URL(string: s), url.scheme != nil else { throw APIClientError.invalidBaseURL }
        return url
    }

    private func makeURL(path: String, queryItems: [URLQueryItem] = []) throws -> URL {
        let base = try baseURL()
        var components = URLComponents(url: base, resolvingAgainstBaseURL: false)!
        let p = path.hasPrefix("/") ? path : "/" + path
        components.path = p
        if !queryItems.isEmpty { components.queryItems = queryItems }
        guard let url = components.url else { throw APIClientError.invalidBaseURL }
        return url
    }

    /// Multipart POST with `file` field (same as FastAPI `UploadFile`).
    private func postMultipart(
        path: String,
        fileURL: URL,
        queryItems: [URLQueryItem] = []
    ) async throws -> Data {
        let url = try makeURL(path: path, queryItems: queryItems)

        let boundary = "Boundary-\(UUID().uuidString)"
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("multipart/form-data; boundary=\(boundary)", forHTTPHeaderField: "Content-Type")

        let fileData = try Data(contentsOf: fileURL)
        let filename = fileURL.lastPathComponent
        var body = Data()
        body.append("--\(boundary)\r\n".data(using: .utf8)!)
        body.append("Content-Disposition: form-data; name=\"file\"; filename=\"\(filename)\"\r\n".data(using: .utf8)!)
        body.append("Content-Type: application/octet-stream\r\n\r\n".data(using: .utf8)!)
        body.append(fileData)
        body.append("\r\n--\(boundary)--\r\n".data(using: .utf8)!)
        request.httpBody = body

        let (data, response) = try await session.data(for: request)
        try throwIfHTTPError(data: data, response: response)
        return data
    }

    private func postJSON<T: Encodable>(path: String, body: T, queryItems: [URLQueryItem] = []) async throws -> Data {
        let url = try makeURL(path: path, queryItems: queryItems)

        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        let enc = JSONEncoder()
        enc.keyEncodingStrategy = .convertToSnakeCase
        request.httpBody = try enc.encode(body)

        let (data, response) = try await session.data(for: request)
        try throwIfHTTPError(data: data, response: response)
        return data
    }

    private func get(path: String) async throws -> Data {
        let url = try makeURL(path: path)
        var request = URLRequest(url: url)
        request.httpMethod = "GET"
        let (data, response) = try await session.data(for: request)
        try throwIfHTTPError(data: data, response: response)
        return data
    }

    private func throwIfHTTPError(data: Data, response: URLResponse) throws {
        guard let http = response as? HTTPURLResponse else { return }
        guard (200...299).contains(http.statusCode) else {
            let msg: String
            if let err = try? JSONDecoder().decode(FastAPIErrorDetail.self, from: data) {
                msg = err.detail
            } else {
                msg = String(data: data, encoding: .utf8) ?? "(no body)"
            }
            throw APIClientError.badStatus(http.statusCode, msg)
        }
    }

    // MARK: Public API

    func health() async throws -> String {
        let data = try await get(path: "health")
        return String(data: data, encoding: .utf8) ?? "{}"
    }

    func detectChords(fileURL: URL) async throws -> ChordList {
        let data = try await postMultipart(path: "detect/chords", fileURL: fileURL)
        return try decoder().decode(ChordList.self, from: data)
    }

    func detectFull(fileURL: URL, instrument: String) async throws -> FullDetectionResponse {
        let data = try await postMultipart(
            path: "detect/full",
            fileURL: fileURL,
            queryItems: [URLQueryItem(name: "instrument", value: instrument)]
        )
        return try decoder().decode(FullDetectionResponse.self, from: data)
    }

    func generateSheet(
        fileURL: URL,
        outputType: String,
        title: String,
        tempo: Int,
        timeSignature: String,
        instrument: String,
        correctionStrength: Double
    ) async throws -> GeneratedSheet {
        let data = try await postMultipart(
            path: "generate/sheet",
            fileURL: fileURL,
            queryItems: [
                URLQueryItem(name: "output_format", value: "musicxml"),
                URLQueryItem(name: "output_type", value: outputType),
                URLQueryItem(name: "title", value: title),
                URLQueryItem(name: "tempo", value: "\(tempo)"),
                URLQueryItem(name: "time_signature", value: timeSignature),
                URLQueryItem(name: "instrument", value: instrument),
                URLQueryItem(name: "correction_strength", value: "\(correctionStrength)"),
            ]
        )
        return try decoder().decode(GeneratedSheet.self, from: data)
    }

    func convertModeChords(chords: ChordList, targetMode: String) async throws -> ChordList {
        let data = try await postJSON(
            path: "arrange/convert-mode/chords",
            body: chords,
            queryItems: [URLQueryItem(name: "target_mode", value: targetMode)]
        )
        return try decoder().decode(ChordList.self, from: data)
    }

    func generateMelody(fileURL: URL, style: String, tempo: Int) async throws -> Data {
        try await postMultipart(
            path: "generate/melody",
            fileURL: fileURL,
            queryItems: [
                URLQueryItem(name: "style", value: style),
                URLQueryItem(name: "tempo", value: "\(tempo)"),
            ]
        )
    }
}
