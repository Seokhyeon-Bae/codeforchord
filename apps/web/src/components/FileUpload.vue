<script setup>
import { ref, computed, onUnmounted } from 'vue'

const emit = defineEmits(['file-selected'])

const isDragging = ref(false)
const fileInput = ref(null)

const supportedFormats = ['.wav', '.mp3', '.flac', '.ogg', '.m4a', '.webm']

// Recording state
const isRecording = ref(false)
const isPaused = ref(false)
const isConverting = ref(false)
const recordingTime = ref(0)
const mediaRecorder = ref(null)
const audioChunks = ref([])
const recordingInterval = ref(null)
const audioStream = ref(null)

// Format recording time as MM:SS
const formattedTime = computed(() => {
  const mins = Math.floor(recordingTime.value / 60)
  const secs = recordingTime.value % 60
  return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`
})

const handleDrop = (e) => {
  isDragging.value = false
  const files = e.dataTransfer.files
  if (files.length > 0) {
    handleFile(files[0])
  }
}

const handleFileSelect = (e) => {
  const files = e.target.files
  if (files.length > 0) {
    handleFile(files[0])
  }
}

const handleFile = (file) => {
  const ext = '.' + file.name.split('.').pop().toLowerCase()
  if (!supportedFormats.includes(ext)) {
    alert(`Unsupported format. Please use: ${supportedFormats.join(', ')}`)
    return
  }
  emit('file-selected', file)
}

const openFilePicker = () => {
  fileInput.value?.click()
}

// Recording functions
const startRecording = async () => {
  try {
    // Request microphone access
    const stream = await navigator.mediaDevices.getUserMedia({ 
      audio: {
        echoCancellation: true,
        noiseSuppression: true,
        sampleRate: 44100,
      }
    })
    audioStream.value = stream
    
    // Determine supported MIME type
    const mimeType = MediaRecorder.isTypeSupported('audio/webm;codecs=opus') 
      ? 'audio/webm;codecs=opus'
      : MediaRecorder.isTypeSupported('audio/webm')
        ? 'audio/webm'
        : 'audio/mp4'
    
    mediaRecorder.value = new MediaRecorder(stream, { mimeType })
    audioChunks.value = []
    
    mediaRecorder.value.ondataavailable = (event) => {
      if (event.data.size > 0) {
        audioChunks.value.push(event.data)
      }
    }
    
    mediaRecorder.value.onstop = async () => {
      isConverting.value = true
      
      try {
        // Create blob from chunks
        const webmBlob = new Blob(audioChunks.value, { type: mimeType })
        
        // Convert to WAV
        const wavBlob = await convertToWav(webmBlob)
        
        // Create a File object from the WAV blob
        const timestamp = new Date().toISOString().replace(/[:.]/g, '-')
        const fileName = `recording-${timestamp}.wav`
        const file = new File([wavBlob], fileName, { type: 'audio/wav' })
        
        // Emit the file
        emit('file-selected', file)
      } catch (err) {
        console.error('Error converting to WAV:', err)
        // Fallback to WebM if conversion fails
        const mimeExt = mimeType.includes('webm') ? 'webm' : 'mp4'
        const blob = new Blob(audioChunks.value, { type: mimeType })
        const timestamp = new Date().toISOString().replace(/[:.]/g, '-')
        const fileName = `recording-${timestamp}.${mimeExt}`
        const file = new File([blob], fileName, { type: mimeType })
        emit('file-selected', file)
      } finally {
        isConverting.value = false
        cleanupRecording()
      }
    }
    
    // Start recording
    mediaRecorder.value.start(1000) // Collect data every second
    isRecording.value = true
    isPaused.value = false
    recordingTime.value = 0
    
    // Start timer
    recordingInterval.value = setInterval(() => {
      if (!isPaused.value) {
        recordingTime.value++
      }
    }, 1000)
    
  } catch (err) {
    console.error('Error accessing microphone:', err)
    alert('Could not access microphone. Please ensure you have granted permission.')
  }
}

const pauseRecording = () => {
  if (mediaRecorder.value && mediaRecorder.value.state === 'recording') {
    mediaRecorder.value.pause()
    isPaused.value = true
  }
}

const resumeRecording = () => {
  if (mediaRecorder.value && mediaRecorder.value.state === 'paused') {
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
  if (mediaRecorder.value && mediaRecorder.value.state !== 'inactive') {
    mediaRecorder.value.stop()
  }
  cleanupRecording()
}

const cleanupRecording = () => {
  // Stop all tracks
  if (audioStream.value) {
    audioStream.value.getTracks().forEach(track => track.stop())
    audioStream.value = null
  }
  
  // Clear interval
  if (recordingInterval.value) {
    clearInterval(recordingInterval.value)
    recordingInterval.value = null
  }
  
  isRecording.value = false
  isPaused.value = false
  recordingTime.value = 0
  audioChunks.value = []
}

// Convert audio blob to WAV
const convertToWav = async (audioBlob) => {
  return new Promise((resolve, reject) => {
    const ctx = new (window.AudioContext || window.webkitAudioContext)()
    
    const reader = new FileReader()
    reader.onload = async () => {
      try {
        // Decode the audio data
        const audioBuffer = await ctx.decodeAudioData(reader.result)
        
        // Convert to WAV
        const wavBlob = audioBufferToWav(audioBuffer)
        
        ctx.close()
        resolve(wavBlob)
      } catch (err) {
        ctx.close()
        reject(err)
      }
    }
    
    reader.onerror = () => reject(reader.error)
    reader.readAsArrayBuffer(audioBlob)
  })
}

// Convert AudioBuffer to WAV Blob
const audioBufferToWav = (buffer) => {
  const numChannels = buffer.numberOfChannels
  const sampleRate = buffer.sampleRate
  const format = 1 // PCM
  const bitDepth = 16
  
  // Interleave channels
  let interleaved
  if (numChannels === 2) {
    const left = buffer.getChannelData(0)
    const right = buffer.getChannelData(1)
    interleaved = new Float32Array(left.length + right.length)
    for (let i = 0, j = 0; i < left.length; i++, j += 2) {
      interleaved[j] = left[i]
      interleaved[j + 1] = right[i]
    }
  } else {
    interleaved = buffer.getChannelData(0)
  }
  
  // Create WAV file
  const dataLength = interleaved.length * (bitDepth / 8)
  const headerLength = 44
  const totalLength = headerLength + dataLength
  
  const arrayBuffer = new ArrayBuffer(totalLength)
  const view = new DataView(arrayBuffer)
  
  // RIFF header
  writeString(view, 0, 'RIFF')
  view.setUint32(4, totalLength - 8, true)
  writeString(view, 8, 'WAVE')
  
  // fmt chunk
  writeString(view, 12, 'fmt ')
  view.setUint32(16, 16, true) // chunk size
  view.setUint16(20, format, true)
  view.setUint16(22, numChannels, true)
  view.setUint32(24, sampleRate, true)
  view.setUint32(28, sampleRate * numChannels * (bitDepth / 8), true) // byte rate
  view.setUint16(32, numChannels * (bitDepth / 8), true) // block align
  view.setUint16(34, bitDepth, true)
  
  // data chunk
  writeString(view, 36, 'data')
  view.setUint32(40, dataLength, true)
  
  // Write audio data
  const offset = 44
  for (let i = 0; i < interleaved.length; i++) {
    const sample = Math.max(-1, Math.min(1, interleaved[i]))
    const intSample = sample < 0 ? sample * 0x8000 : sample * 0x7FFF
    view.setInt16(offset + i * 2, intSample, true)
  }
  
  return new Blob([arrayBuffer], { type: 'audio/wav' })
}

// Helper to write string to DataView
const writeString = (view, offset, string) => {
  for (let i = 0; i < string.length; i++) {
    view.setUint8(offset + i, string.charCodeAt(i))
  }
}

// Cleanup on unmount
onUnmounted(() => {
  cleanupRecording()
})
</script>

<template>
  <div class="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
    <h2 class="text-xl font-semibold text-gray-900 mb-2">Upload Audio</h2>
    <p class="text-gray-600 mb-6">Upload a music file to detect chords, generate sheet music, and more.</p>
    
    <!-- Drop Zone -->
    <div
      :class="[
        'border-2 border-dashed rounded-xl p-8 text-center transition-colors cursor-pointer',
        isDragging 
          ? 'border-sky-500 bg-sky-50' 
          : 'border-gray-300 hover:border-sky-400 hover:bg-sky-50'
      ]"
      @dragover.prevent="isDragging = true"
      @dragleave="isDragging = false"
      @drop.prevent="handleDrop"
      @click="openFilePicker"
    >
      <input
        ref="fileInput"
        type="file"
        accept=".wav,.mp3,.flac,.ogg,.m4a"
        class="hidden"
        @change="handleFileSelect"
      />
      
      <div class="flex flex-col items-center">
        <div class="w-16 h-16 bg-sky-100 rounded-full flex items-center justify-center mb-4">
          <svg class="w-8 h-8 text-sky-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
          </svg>
        </div>
        
        <p class="text-lg font-medium text-gray-700 mb-1">
          Drop your audio file here
        </p>
        <p class="text-gray-500 mb-4">or click to browse</p>
        
        <div class="flex flex-wrap justify-center gap-2">
          <span 
            v-for="format in supportedFormats" 
            :key="format"
            class="px-2 py-1 bg-gray-100 rounded text-xs text-gray-600 font-mono"
          >
            {{ format }}
          </span>
        </div>
      </div>
    </div>
    
    <!-- Record Option -->
    <div class="mt-6 pt-6 border-t border-gray-200">
      <!-- Not Recording State -->
      <div v-if="!isRecording && !isConverting">
        <button 
          @click="startRecording"
          class="w-full px-4 py-3 rounded-lg font-medium flex items-center justify-center space-x-2 bg-red-50 text-red-600 hover:bg-red-100 transition-colors cursor-pointer"
        >
          <svg class="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
            <path fill-rule="evenodd" d="M7 4a3 3 0 016 0v4a3 3 0 11-6 0V4zm4 10.93A7.001 7.001 0 0017 8a1 1 0 10-2 0A5 5 0 015 8a1 1 0 00-2 0 7.001 7.001 0 006 6.93V17H6a1 1 0 100 2h8a1 1 0 100-2h-3v-2.07z" clip-rule="evenodd" />
          </svg>
          <span>Record Audio</span>
        </button>
        <p class="text-center text-xs text-gray-500 mt-2">Click to start recording from your microphone</p>
      </div>
      
      <!-- Converting State -->
      <div v-else-if="isConverting" class="space-y-4">
        <div class="flex items-center justify-center space-x-3 py-6 bg-sky-50 rounded-lg">
          <svg class="w-6 h-6 text-sky-600 animate-spin" fill="none" viewBox="0 0 24 24">
            <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
            <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
          </svg>
          <span class="text-lg font-medium text-sky-700">Converting to WAV...</span>
        </div>
      </div>
      
      <!-- Recording State -->
      <div v-else-if="isRecording" class="space-y-4">
        <!-- Recording indicator -->
        <div class="flex items-center justify-center space-x-3 py-4 bg-red-50 rounded-lg">
          <span 
            :class="[
              'w-3 h-3 rounded-full',
              isPaused ? 'bg-yellow-500' : 'bg-red-500 animate-pulse'
            ]"
          ></span>
          <span class="text-2xl font-mono font-bold text-gray-800">{{ formattedTime }}</span>
          <span class="text-sm text-gray-500">{{ isPaused ? 'Paused' : 'Recording...' }}</span>
        </div>
        
        <!-- Recording controls -->
        <div class="flex items-center justify-center space-x-3">
          <!-- Pause/Resume -->
          <button 
            v-if="!isPaused"
            @click="pauseRecording"
            class="px-4 py-2 rounded-lg font-medium flex items-center space-x-2 bg-yellow-50 text-yellow-600 hover:bg-yellow-100 transition-colors"
          >
            <svg class="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
              <path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zM7 8a1 1 0 012 0v4a1 1 0 11-2 0V8zm5-1a1 1 0 00-1 1v4a1 1 0 102 0V8a1 1 0 00-1-1z" clip-rule="evenodd" />
            </svg>
            <span>Pause</span>
          </button>
          <button 
            v-else
            @click="resumeRecording"
            class="px-4 py-2 rounded-lg font-medium flex items-center space-x-2 bg-green-50 text-green-600 hover:bg-green-100 transition-colors"
          >
            <svg class="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
              <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM9.555 7.168A1 1 0 008 8v4a1 1 0 001.555.832l3-2a1 1 0 000-1.664l-3-2z" clip-rule="evenodd" />
            </svg>
            <span>Resume</span>
          </button>
          
          <!-- Stop (save) -->
          <button 
            @click="stopRecording"
            class="px-4 py-2 rounded-lg font-medium flex items-center space-x-2 bg-sky-50 text-sky-600 hover:bg-sky-100 transition-colors"
          >
            <svg class="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
              <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8 7a1 1 0 00-1 1v4a1 1 0 001 1h4a1 1 0 001-1V8a1 1 0 00-1-1H8z" clip-rule="evenodd" />
            </svg>
            <span>Stop & Use</span>
          </button>
          
          <!-- Cancel -->
          <button 
            @click="cancelRecording"
            class="px-4 py-2 rounded-lg font-medium flex items-center space-x-2 bg-gray-100 text-gray-600 hover:bg-gray-200 transition-colors"
          >
            <svg class="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
              <path fill-rule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clip-rule="evenodd" />
            </svg>
            <span>Cancel</span>
          </button>
        </div>
        
        <p class="text-center text-xs text-gray-500">
          Click "Stop & Use" to finish recording and analyze the audio
        </p>
      </div>
    </div>
  </div>
</template>
