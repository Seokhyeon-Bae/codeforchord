<script setup>
import { ref } from 'vue'

const emit = defineEmits(['file-selected'])

const isDragging = ref(false)
const fileInput = ref(null)

const supportedFormats = ['.wav', '.mp3', '.flac', '.ogg', '.m4a']

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
      <button class="w-full px-4 py-2 rounded-lg font-medium flex items-center justify-center space-x-2 bg-red-50 text-red-600 hover:bg-red-100 transition-colors cursor-pointer">
        <svg class="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
          <path fill-rule="evenodd" d="M7 4a3 3 0 016 0v4a3 3 0 11-6 0V4zm4 10.93A7.001 7.001 0 0017 8a1 1 0 10-2 0A5 5 0 015 8a1 1 0 00-2 0 7.001 7.001 0 006 6.93V17H6a1 1 0 100 2h8a1 1 0 100-2h-3v-2.07z" clip-rule="evenodd" />
        </svg>
        <span>Record Audio</span>
      </button>
      <p class="text-center text-xs text-gray-500 mt-2">Coming soon</p>
    </div>
  </div>
</template>
