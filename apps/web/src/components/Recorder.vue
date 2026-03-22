<script setup>
import { ref, computed, onUnmounted } from 'vue'

const emit = defineEmits(['file-selected'])

// Recording state
const isRecording = ref(false)
const isPaused = ref(false)
const isConverting = ref(false)
const recordingTime = ref(0)
const mediaRecorder = ref(null)
const audioChunks = ref([])
const recordingInterval = ref(null)
const audioStream = ref(null)

// Waveform
const canvasRef = ref(null)
let analyser = null
let animationId = null
let audioCtxForViz = null

const formattedTime = computed(() => {
  const mins = Math.floor(recordingTime.value / 60)
  const secs = recordingTime.value % 60
  return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`
})

// ── Waveform visualizer ─────────────────────────────────────────────────────

const startVisualizer = (stream) => {
  audioCtxForViz = new (window.AudioContext || window.webkitAudioContext)()
  const source = audioCtxForViz.createMediaStreamSource(stream)
  analyser = audioCtxForViz.createAnalyser()
  analyser.fftSize = 1024
  source.connect(analyser)
  drawWaveform()
}

const drawWaveform = () => {
  if (!analyser || !canvasRef.value) return
  const canvas = canvasRef.value
  const ctx = canvas.getContext('2d')
  const bufferLength = analyser.frequencyBinCount
  const dataArray = new Uint8Array(bufferLength)

  const draw = () => {
    animationId = requestAnimationFrame(draw)
    analyser.getByteTimeDomainData(dataArray)

    ctx.clearRect(0, 0, canvas.width, canvas.height)

    // Background
    ctx.fillStyle = '#f0f9ff'
    ctx.fillRect(0, 0, canvas.width, canvas.height)

    // Waveform line
    ctx.lineWidth = 2
    ctx.strokeStyle = isPaused.value ? '#f59e0b' : '#0284c7'
    ctx.beginPath()

    const sliceWidth = canvas.width / bufferLength
    let x = 0
    for (let i = 0; i < bufferLength; i++) {
      const v = dataArray[i] / 128.0
      const y = (v * canvas.height) / 2
      if (i === 0) ctx.moveTo(x, y)
      else ctx.lineTo(x, y)
      x += sliceWidth
    }
    ctx.lineTo(canvas.width, canvas.height / 2)
    ctx.stroke()
  }
  draw()
}

const stopVisualizer = () => {
  if (animationId) {
    cancelAnimationFrame(animationId)
    animationId = null
  }
  if (audioCtxForViz) {
    audioCtxForViz.close()
    audioCtxForViz = null
  }
  analyser = null

  // Clear canvas
  if (canvasRef.value) {
    const ctx = canvasRef.value.getContext('2d')
    ctx.clearRect(0, 0, canvasRef.value.width, canvasRef.value.height)
  }
}

// ── Recording controls ──────────────────────────────────────────────────────

const startRecording = async () => {
  try {
    const stream = await navigator.mediaDevices.getUserMedia({
      audio: { echoCancellation: true, noiseSuppression: true, sampleRate: 44100 },
    })
    audioStream.value = stream

    const mimeType = MediaRecorder.isTypeSupported('audio/webm;codecs=opus')
      ? 'audio/webm;codecs=opus'
      : MediaRecorder.isTypeSupported('audio/webm')
        ? 'audio/webm'
        : 'audio/mp4'

    mediaRecorder.value = new MediaRecorder(stream, { mimeType })
    audioChunks.value = []

    mediaRecorder.value.ondataavailable = (e) => {
      if (e.data.size > 0) audioChunks.value.push(e.data)
    }

    mediaRecorder.value.onstop = async () => {
      stopVisualizer()
      isConverting.value = true
      try {
        const webmBlob = new Blob(audioChunks.value, { type: mimeType })
        const wavBlob = await convertToWav(webmBlob)
        const timestamp = new Date().toISOString().replace(/[:.]/g, '-')
        const file = new File([wavBlob], `recording-${timestamp}.wav`, { type: 'audio/wav' })
        emit('file-selected', file)
      } catch {
        // Fallback: send as-is
        const ext = mimeType.includes('webm') ? 'webm' : 'mp4'
        const blob = new Blob(audioChunks.value, { type: mimeType })
        const timestamp = new Date().toISOString().replace(/[:.]/g, '-')
        const file = new File([blob], `recording-${timestamp}.${ext}`, { type: mimeType })
        emit('file-selected', file)
      } finally {
        isConverting.value = false
        cleanup()
      }
    }

    mediaRecorder.value.start(100)
    isRecording.value = true
    isPaused.value = false
    recordingTime.value = 0
    recordingInterval.value = setInterval(() => { if (!isPaused.value) recordingTime.value++ }, 1000)
    startVisualizer(stream)
  } catch {
    alert('마이크 접근 권한이 필요해요. 브라우저 설정에서 허용해주세요.')
  }
}

const pauseRecording = () => {
  if (mediaRecorder.value?.state === 'recording') {
    mediaRecorder.value.pause()
    isPaused.value = true
  }
}

const resumeRecording = () => {
  if (mediaRecorder.value?.state === 'paused') {
    mediaRecorder.value.resume()
    isPaused.value = false
  }
}

const stopRecording = () => {
  if (mediaRecorder.value && mediaRecorder.value.state !== 'inactive') {
    mediaRecorder.value.stop()
  }
}

const cancelRecording = () => {
  // Prevent onstop from emitting a file
  if (mediaRecorder.value) {
    mediaRecorder.value.onstop = null
    if (mediaRecorder.value.state !== 'inactive') mediaRecorder.value.stop()
  }
  stopVisualizer()
  cleanup()
}

const cleanup = () => {
  audioStream.value?.getTracks().forEach(t => t.stop())
  audioStream.value = null
  if (recordingInterval.value) {
    clearInterval(recordingInterval.value)
    recordingInterval.value = null
  }
  isRecording.value = false
  isPaused.value = false
  recordingTime.value = 0
  audioChunks.value = []
}

// ── WAV conversion ──────────────────────────────────────────────────────────

const convertToWav = (blob) =>
  new Promise((resolve, reject) => {
    const ctx = new (window.AudioContext || window.webkitAudioContext)()
    const reader = new FileReader()
    reader.onload = async () => {
      try {
        const audioBuffer = await ctx.decodeAudioData(reader.result)
        resolve(audioBufferToWav(audioBuffer))
        ctx.close()
      } catch (e) { ctx.close(); reject(e) }
    }
    reader.onerror = () => reject(reader.error)
    reader.readAsArrayBuffer(blob)
  })

const audioBufferToWav = (buffer) => {
  const numCh = buffer.numberOfChannels
  const sr = buffer.sampleRate
  let interleaved
  if (numCh === 2) {
    const l = buffer.getChannelData(0), r = buffer.getChannelData(1)
    interleaved = new Float32Array(l.length + r.length)
    for (let i = 0, j = 0; i < l.length; i++, j += 2) {
      interleaved[j] = l[i]; interleaved[j + 1] = r[i]
    }
  } else {
    interleaved = buffer.getChannelData(0)
  }
  const dataLen = interleaved.length * 2
  const buf = new ArrayBuffer(44 + dataLen)
  const v = new DataView(buf)
  const ws = (off, s) => { for (let i = 0; i < s.length; i++) v.setUint8(off + i, s.charCodeAt(i)) }
  ws(0, 'RIFF'); v.setUint32(4, 36 + dataLen, true); ws(8, 'WAVE')
  ws(12, 'fmt '); v.setUint32(16, 16, true); v.setUint16(20, 1, true)
  v.setUint16(22, numCh, true); v.setUint32(24, sr, true)
  v.setUint32(28, sr * numCh * 2, true); v.setUint16(32, numCh * 2, true)
  v.setUint16(34, 16, true); ws(36, 'data'); v.setUint32(40, dataLen, true)
  for (let i = 0; i < interleaved.length; i++) {
    const s = Math.max(-1, Math.min(1, interleaved[i]))
    v.setInt16(44 + i * 2, s < 0 ? s * 0x8000 : s * 0x7FFF, true)
  }
  return new Blob([buf], { type: 'audio/wav' })
}

onUnmounted(() => { cancelRecording() })
</script>

<template>
  <div class="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
    <h2 class="text-xl font-semibold text-gray-900 mb-2">Record Audio</h2>
    <p class="text-gray-500 text-sm mb-6">마이크로 직접 녹음하고 바로 분석하세요.</p>

    <!-- Idle -->
    <div v-if="!isRecording && !isConverting" class="flex flex-col items-center gap-4">
      <div class="w-24 h-24 rounded-full bg-red-50 flex items-center justify-center border-4 border-red-100">
        <svg class="w-10 h-10 text-red-500" fill="currentColor" viewBox="0 0 20 20">
          <path fill-rule="evenodd" d="M7 4a3 3 0 016 0v4a3 3 0 11-6 0V4zm4 10.93A7.001 7.001 0 0017 8a1 1 0 10-2 0A5 5 0 015 8a1 1 0 00-2 0 7.001 7.001 0 006 6.93V17H6a1 1 0 100 2h8a1 1 0 100-2h-3v-2.07z" clip-rule="evenodd" />
        </svg>
      </div>
      <button
        @click="startRecording"
        class="px-8 py-3 bg-red-500 hover:bg-red-600 text-white rounded-full font-semibold text-lg transition-colors cursor-pointer shadow-md"
      >
        녹음 시작
      </button>
      <p class="text-xs text-gray-400">클릭하면 마이크 접근 권한을 요청합니다</p>
    </div>

    <!-- Converting -->
    <div v-else-if="isConverting" class="flex flex-col items-center gap-4 py-8">
      <svg class="w-10 h-10 text-sky-500 animate-spin" fill="none" viewBox="0 0 24 24">
        <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/>
        <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/>
      </svg>
      <p class="text-sky-700 font-medium">WAV로 변환 중...</p>
    </div>

    <!-- Recording -->
    <div v-else class="space-y-5">
      <!-- Waveform canvas -->
      <div class="rounded-xl overflow-hidden border border-sky-100">
        <canvas ref="canvasRef" width="600" height="100" class="w-full h-24 block" />
      </div>

      <!-- Timer + status -->
      <div class="flex items-center justify-center gap-3">
        <span
          :class="['w-3 h-3 rounded-full', isPaused ? 'bg-amber-400' : 'bg-red-500 animate-pulse']"
        />
        <span class="text-3xl font-mono font-bold text-gray-800 tabular-nums">{{ formattedTime }}</span>
        <span class="text-sm text-gray-500">{{ isPaused ? '일시정지' : '녹음 중' }}</span>
      </div>

      <!-- Controls -->
      <div class="flex items-center justify-center gap-3">
        <!-- Pause / Resume -->
        <button
          v-if="!isPaused"
          @click="pauseRecording"
          class="px-4 py-2 rounded-lg font-medium flex items-center gap-2 bg-amber-50 text-amber-600 hover:bg-amber-100 transition-colors cursor-pointer"
        >
          <svg class="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
            <path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zM7 8a1 1 0 012 0v4a1 1 0 11-2 0V8zm5-1a1 1 0 00-1 1v4a1 1 0 102 0V8a1 1 0 00-1-1z" clip-rule="evenodd" />
          </svg>
          일시정지
        </button>
        <button
          v-else
          @click="resumeRecording"
          class="px-4 py-2 rounded-lg font-medium flex items-center gap-2 bg-green-50 text-green-600 hover:bg-green-100 transition-colors cursor-pointer"
        >
          <svg class="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
            <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM9.555 7.168A1 1 0 008 8v4a1 1 0 001.555.832l3-2a1 1 0 000-1.664l-3-2z" clip-rule="evenodd" />
          </svg>
          계속 녹음
        </button>

        <!-- Stop & use -->
        <button
          @click="stopRecording"
          class="px-5 py-2 rounded-lg font-semibold flex items-center gap-2 bg-sky-600 text-white hover:bg-sky-700 transition-colors cursor-pointer shadow"
        >
          <svg class="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
            <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8 7a1 1 0 00-1 1v4a1 1 0 001 1h4a1 1 0 001-1V8a1 1 0 00-1-1H8z" clip-rule="evenodd" />
          </svg>
          완료 & 분석
        </button>

        <!-- Cancel -->
        <button
          @click="cancelRecording"
          class="px-4 py-2 rounded-lg font-medium flex items-center gap-2 bg-gray-100 text-gray-500 hover:bg-gray-200 transition-colors cursor-pointer"
        >
          <svg class="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
            <path fill-rule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clip-rule="evenodd" />
          </svg>
          취소
        </button>
      </div>

      <p class="text-center text-xs text-gray-400">
        "완료 & 분석"을 누르면 WAV로 변환 후 자동으로 분석 탭으로 이동합니다
      </p>
    </div>
  </div>
</template>
