<script setup>
import { watch, onMounted, onUnmounted } from 'vue'

const props = defineProps({
  open: { type: Boolean, default: false },
  section: { type: String, default: null }, // 'how' | 'pricing' | 'api'
})

const emit = defineEmits(['close'])

function close() {
  emit('close')
}

function onKeydown(e) {
  if (e.key === 'Escape' && props.open) close()
}

onMounted(() => window.addEventListener('keydown', onKeydown))
onUnmounted(() => {
  window.removeEventListener('keydown', onKeydown)
  document.body.style.overflow = ''
})

watch(
  () => props.open,
  (v) => {
    document.body.style.overflow = v ? 'hidden' : ''
  },
)
</script>

<template>
  <Teleport to="body">
    <Transition
      enter-active-class="transition-opacity duration-200"
      leave-active-class="transition-opacity duration-200"
      enter-from-class="opacity-0"
      leave-to-class="opacity-0"
    >
      <div
        v-if="open && section"
        class="fixed inset-0 z-[100] flex items-center justify-center p-4 sm:p-6"
        role="dialog"
        aria-modal="true"
        :aria-labelledby="'nav-modal-title'"
      >
        <div
          class="absolute inset-0 bg-black/70 backdrop-blur-sm"
          @click.self="close"
        />
        <div
          class="relative w-full max-w-lg max-h-[85vh] overflow-y-auto rounded-2xl border border-[#3a3a42] bg-[#242429] shadow-2xl"
        >
          <div class="sticky top-0 flex items-center justify-between gap-4 border-b border-[#3a3a42] bg-[#242429]/95 px-5 py-4 backdrop-blur-sm">
            <h2 id="nav-modal-title" class="text-lg font-semibold text-[#f5f5f5]">
              <template v-if="section === 'how'">How it works</template>
              <template v-else-if="section === 'pricing'">Pricing</template>
              <template v-else>API</template>
            </h2>
            <button
              type="button"
              class="rounded-lg px-3 py-1.5 text-sm font-medium text-[#a0a0a8] hover:bg-[#333338] hover:text-[#f5f5f5] cursor-pointer"
              aria-label="Close"
              @click="close"
            >
              Close
            </button>
          </div>

          <div class="px-5 py-5 text-sm text-[#c4c4cc] space-y-4 leading-relaxed">
            <!-- How it works -->
            <template v-if="section === 'how'">
              <p>
                CodeForChord takes <strong class="text-[#f5f5f5]">uploaded</strong> or
                <strong class="text-[#f5f5f5]">recorded</strong> audio, runs
                <strong class="text-[#f5f5f5]">ML analysis</strong> for chords and notes, then connects to
                <strong class="text-[#f5f5f5]">sheet music</strong>,
                <strong class="text-[#f5f5f5]">arrangement</strong>, and export as
                <strong class="text-[#f5f5f5]">MusicXML</strong> or <strong class="text-[#f5f5f5]">MIDI</strong>.
              </p>
              <ol class="list-decimal pl-5 space-y-2 text-[#a0a0a8]">
                <li><span class="text-[#d4a55a]">Input</span> — Upload files (e.g. MP3/WAV) or record in the browser.</li>
                <li><span class="text-[#d4a55a]">ML analysis</span> — Chord detection, pitch/note extraction (e.g. Basic Pitch), tempo and meter.</li>
                <li><span class="text-[#d4a55a]">Sheet &amp; arrange</span> — Notation, transpose, simplify chords, melody ideas, and related tools.</li>
                <li><span class="text-[#d4a55a]">Export</span> — MusicXML and MIDI for MuseScore, DAWs, and more.</li>
              </ol>
              <p class="text-xs text-[#6b6b73] border-t border-[#3a3a42] pt-4">
                <strong class="text-[#a0a0a8]">Stack:</strong>
                Auth0 (auth), MongoDB (data/history), Azure Blob Storage (audio; e.g. LRU as implemented).
              </p>
            </template>

            <!-- Pricing -->
            <template v-else-if="section === 'pricing'">
              <p class="text-[#d4a55a] font-semibold text-base">Congrats! 🎉</p>
              <p>
                <strong class="text-[#f5f5f5]">You have been selected as a free beta tester.</strong>
              </p>
              <p>
                During the <strong class="text-[#f5f5f5]">beta</strong>, pricing is
                <strong class="text-[#f5f5f5]">$0</strong> (beta only). We ship features; your bug reports and feedback matter most.
              </p>
              <p class="text-xs text-[#8a8a92] border border-[#3a3a42] rounded-lg p-3 bg-[#1a1a1f]/80">
                <strong class="text-[#a0a0a8]">Hackathon / demo:</strong>
                Rewrite this copy before any production launch.
              </p>
            </template>

            <!-- API -->
            <template v-else-if="section === 'api'">
              <p>
                The backend is <strong class="text-[#f5f5f5]">FastAPI</strong>. Audio, chord/note analysis, and MusicXML generation are exposed as
                <strong class="text-[#f5f5f5]">REST</strong> APIs for the web and iOS clients.
              </p>
              <ul class="list-disc pl-5 space-y-2 text-[#a0a0a8]">
                <li>
                  <strong class="text-[#d4a55a]">Auth:</strong>
                  Auth0 JWT — protected routes use <code class="text-[#c4b5fd] bg-[#1a1a1f] px-1 rounded">Authorization: Bearer &lt;token&gt;</code>.
                </li>
                <li>
                  <strong class="text-[#d4a55a]">Docs:</strong>
                  OpenAPI and <code class="text-[#c4b5fd] bg-[#1a1a1f] px-1 rounded">/docs</code> (Swagger) on your deployment.
                </li>
                <li>
                  <strong class="text-[#d4a55a]">Public policy:</strong>
                  API keys, rate limits, and versioning (e.g. v1) are planned after beta.
                </li>
              </ul>
              <p class="text-xs text-[#6b6b73]">
                See the repo README for Basic Pitch, Librosa, Music21, Azure, MongoDB, and more.
              </p>
            </template>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>
