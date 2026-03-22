# CodeForChord — Native iOS (Xcode)

This folder is a **SwiftUI** app you can open and run in **Xcode** immediately on a Mac.

## Open and run

1. Clone the repo on a Mac with **Xcode 15+**.
2. Open the project file:
   ```bash
   open apps/ios/CodeForChord.xcodeproj
   ```
3. Select an **iPhone simulator** (or a device).
4. Press **Run** (⌘R).

No CocoaPods or Flutter — only Xcode.

## Backend URL

Default API base URL is `http://127.0.0.1:8000` (iOS Simulator → your Mac).

- Start the FastAPI server: `uvicorn app.main:app --reload --port 8000` in `services/audio-processor`.
- On a **physical iPhone**, open **Settings** (gear in the app), set your Mac’s **LAN IP**, e.g. `http://192.168.1.10:8000`.

`Info.plist` enables **local network** HTTP via `NSAllowsLocalNetworking`.

## App icon (optional)

Add an **App Icon** set in `Assets.xcassets` in Xcode if you want a custom icon; the project runs without one (default Xcode / system placeholder).

## Remote / CI

- **SSH into a Mac** and open the same `.xcodeproj`.
- **GitHub Actions**: see `.github/workflows/ios-native.yml` for a simulator build on `macos-latest`.

## Signing (device / TestFlight)

In Xcode → **Signing & Capabilities**, pick your **Team** (replaces empty `DEVELOPMENT_TEAM` in the project).
