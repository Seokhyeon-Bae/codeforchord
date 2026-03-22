# CodeForChord Mobile App

Flutter mobile app for AI-powered music transcription.

## Features

- **Upload Audio**: Select audio files from device
- **Record Audio**: Record directly from microphone
- **Full Analysis**: Detect both notes and chords
- **Chords Only**: Detect chord progression only
- **Sheet Music Generation**: Generate MusicXML sheet music
- **Mode Conversion**: Convert Major ↔ Minor
- **Melody Suggestion**: Generate melodies from chords

## Prerequisites

1. [Flutter SDK](https://flutter.dev/docs/get-started/install) (3.0+)
2. Android Studio or VS Code with Flutter extension
3. Backend server running at `http://localhost:8000`

## Setup

1. Install dependencies:
```bash
cd apps/mobile
flutter pub get
```

2. Update API base URL in `lib/api/api_client.dart`:
   - Android emulator: `http://10.0.2.2:8000`
   - iOS simulator: `http://localhost:8000`
   - Physical device: Use your computer's IP address

3. Run the app:
```bash
flutter run
```

## Project Structure

```
lib/
├── api/           # API client for backend communication
├── models/        # Data models (Chord, Note)
├── providers/     # State management (Provider)
├── screens/       # Main screens
├── widgets/       # Reusable UI components
├── theme/         # App theme and colors
└── main.dart      # App entry point
```

## Design

- Dark theme with gold accent (#D4A55A)
- Matches web app design language
- Material Design 3 components

## Backend API

The app communicates with the Python backend:
- `POST /detect/chords` - Detect chords
- `POST /detect/full` - Full analysis
- `POST /generate/sheet` - Generate sheet music
- `POST /arrange/convert-mode/chords` - Mode conversion
- `POST /generate/melody` - Generate melody
