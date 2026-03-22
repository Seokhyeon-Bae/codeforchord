<script setup>
import { ref } from 'vue'

const emit = defineEmits(['file-selected'])

const isDragging = ref(false)
const fileInput = ref(null)

const supportedFormats = ['.wav', '.mp3', '.flac', '.ogg', '.m4a', '.webm']

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
  <div class="bg-[#2a2a30]/80 backdrop-blur-sm rounded-xl border border-[#3a3a42] p-8">
    <!-- Hero Section with Image -->
    <div class="relative mb-8 rounded-xl overflow-hidden">
      <img 
        src="/image/guitarpiano.png" 
        alt="Instruments" 
        class="w-full h-48 object-cover opacity-60"
      />
      <div class="absolute inset-0 bg-gradient-to-t from-[#2a2a30] via-transparent to-transparent"></div>
      <div class="absolute bottom-4 left-6">
        <h2 class="text-2xl font-bold text-[#f5f5f5] mb-1">Upload Your Music</h2>
        <p class="text-[#a0a0a8]">Transform audio into sheet music with AI</p>
      </div>
    </div>
    
    <!-- Drop Zone -->
    <div
      :class="[
        'border-2 border-dashed rounded-xl p-10 text-center transition-all cursor-pointer',
        isDragging 
          ? 'border-[#d4a55a] bg-[#d4a55a]/10' 
          : 'border-[#4a4a52] hover:border-[#d4a55a]/50 hover:bg-[#333338]/50'
      ]"
      @dragover.prevent="isDragging = true"
      @dragleave="isDragging = false"
      @drop.prevent="handleDrop"
      @click="openFilePicker"
    >
      <input
        ref="fileInput"
        type="file"
        accept=".wav,.mp3,.flac,.ogg,.m4a,.webm"
        class="hidden"
        @change="handleFileSelect"
      />
      
      <div class="flex flex-col items-center">
        <div class="w-20 h-20 bg-[#d4a55a]/20 rounded-full flex items-center justify-center mb-5">
          <svg class="w-10 h-10 text-[#d4a55a]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
          </svg>
        </div>
        
        <p class="text-lg font-semibold text-[#f5f5f5] mb-2">
          Drop your audio file here
        </p>
        <p class="text-[#6b6b73] mb-5">or click to browse your files</p>
        
        <div class="flex flex-wrap justify-center gap-2">
          <span 
            v-for="format in supportedFormats" 
            :key="format"
            class="px-3 py-1 bg-[#333338] rounded-full text-xs text-[#a0a0a8] font-mono"
          >
            {{ format }}
          </span>
        </div>
      </div>
    </div>
    
    <!-- Features -->
    <div class="mt-8 grid grid-cols-3 gap-4">
      <div class="text-center p-4">
        <div class="w-10 h-10 bg-[#d4a55a]/20 rounded-lg flex items-center justify-center mx-auto mb-3">
          <svg class="w-5 h-5 text-[#d4a55a]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 19V6l12-3v13M9 19c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zm12-3c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zM9 10l12-3" />
          </svg>
        </div>
        <p class="text-sm font-medium text-[#f5f5f5]">Chord Detection</p>
        <p class="text-xs text-[#6b6b73] mt-1">AI-powered analysis</p>
      </div>
      <div class="text-center p-4">
        <div class="w-10 h-10 bg-[#d4a55a]/20 rounded-lg flex items-center justify-center mx-auto mb-3">
          <svg class="w-5 h-5 text-[#d4a55a]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
          </svg>
        </div>
        <p class="text-sm font-medium text-[#f5f5f5]">Sheet Music</p>
        <p class="text-xs text-[#6b6b73] mt-1">Export to MusicXML</p>
      </div>
      <div class="text-center p-4">
        <div class="w-10 h-10 bg-[#d4a55a]/20 rounded-lg flex items-center justify-center mx-auto mb-3">
          <svg class="w-5 h-5 text-[#d4a55a]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 6V4m0 2a2 2 0 100 4m0-4a2 2 0 110 4m-6 8a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4m6 6v10m6-2a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4" />
          </svg>
        </div>
        <p class="text-sm font-medium text-[#f5f5f5]">Arrangement</p>
        <p class="text-xs text-[#6b6b73] mt-1">Transpose & modify</p>
      </div>
    </div>
  </div>
</template>
