# CodeForChord — Header nav copy (How it works / Pricing / API)

English draft for **How it works**, **Pricing**, and **API** links in the site header.  
*(Repo: [Seokhyeon-Bae/codeforchord](https://github.com/Seokhyeon-Bae/codeforchord).)*

---

## How it works

CodeForChord takes **uploaded** or **recorded** audio, runs **ML analysis** to extract **chords and notes**, then connects to **sheet music**, **arrangement tools**, and export as **MusicXML** or **MIDI**.

1. **Input** — Upload audio files (e.g. MP3/WAV) or **record** in the browser.  
2. **ML analysis** — The backend performs **chord detection**, **pitch/note extraction** (e.g. Basic Pitch), tempo and meter detection.  
3. **Sheet & arrangement** — View notation, transpose, simplify chords, melody suggestions, and related **arrangement** features.  
4. **Export** — Download **MusicXML** and **MIDI** for MuseScore, DAWs, and other tools.

**Stack (project-aligned):** **Auth0** for authentication; **MongoDB** for user data and history; **Azure Blob Storage** for audio objects (e.g. LRU policies as implemented in the app).

---

## Pricing

### Congrats! 🎉

**You have been selected as a free beta tester.**

During the **beta**, pricing is **$0** (beta only). We are shipping features; your bug reports and feedback are the real “price tag.”

> **Hackathon / demo:** Review and rewrite this copy before any production launch.

---

## API

The backend is **FastAPI**. Audio processing, chord/note analysis, and MusicXML generation are exposed as **REST** endpoints consumed by the web and iOS clients.

- **Auth:** **Auth0**-issued **JWT**; protected routes expect `Authorization: Bearer <token>`.  
- **Docs:** Use the deployed **OpenAPI** schema and **`/docs`** (Swagger UI) for paths and schemas.  
- **Public policy:** API keys, rate limits, and versioning (e.g. `v1`) are **planned after beta**; treat as internal/beta until then.

For stack details, see the repository **README** (Basic Pitch, Librosa, Music21, Azure, MongoDB, etc.).
