<script setup>
import { useAudioStore } from '../stores/audio'

const store = useAudioStore()

const instruments = [
  { value: 'piano', label: 'Piano', icon: 'M9 19V6l12-3v13M9 19c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zm12-3c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zM9 10l12-3' },
  { value: 'guitar', label: 'Guitar', icon: 'M9 19V6l12-3v13M9 19c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zm12-3c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zM9 10l12-3' },
  { value: 'vocal', label: 'Vocal', icon: 'M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z' },
]
</script>

<template>
  <div class="bg-[#2a2a30]/80 backdrop-blur-sm rounded-xl border border-[#3a3a42] p-6">
    <h2 class="text-xl font-bold text-[#f5f5f5] mb-6">Audio Analysis</h2>
    
    <!-- No File Warning -->
    <div v-if="!store.hasFile" class="text-center py-12">
      <div class="w-20 h-20 bg-[#333338] rounded-full flex items-center justify-center mx-auto mb-4">
        <svg class="w-10 h-10 text-[#6b6b73]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 19V6l12-3v13M9 19c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zm12-3c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zM9 10l12-3" />
        </svg>
      </div>
      <p class="text-[#6b6b73]">Upload an audio file to start analyzing</p>
    </div>
    
    <!-- Analysis Controls -->
    <div v-else class="space-y-6">
      <!-- Cloud Status -->
      <div v-if="store.isUploading" class="flex items-center gap-2 px-4 py-3 bg-[#d4a55a]/10 rounded-lg text-[#d4a55a] text-sm border border-[#d4a55a]/20">
        <svg class="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
          <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/>
          <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/>
        </svg>
        Uploading to Azure...
      </div>
      <div v-else-if="store.blobName" class="flex items-center gap-2 px-4 py-3 bg-green-900/20 rounded-lg text-green-400 text-sm border border-green-800/30">
        <svg class="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
          <path fill-rule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clip-rule="evenodd"/>
        </svg>
        Uploaded to Azure — Will be saved to MongoDB when sheet is generated
      </div>

      <!-- File Info -->
      <div class="flex items-center p-4 bg-[#333338]/50 rounded-xl border border-[#3a3a42]">
        <div class="w-12 h-12 bg-[#d4a55a]/20 rounded-xl flex items-center justify-center mr-4">
          <svg class="w-6 h-6 text-[#d4a55a]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 19V6l12-3v13M9 19c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zm12-3c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zM9 10l12-3" />
          </svg>
        </div>
        <div class="flex-1">
          <p class="font-medium text-[#f5f5f5]">{{ store.fileName }}</p>
          <p class="text-sm text-[#6b6b73]">
            {{ store.fileName?.includes('recording') ? 'Recorded audio' : 'Ready for analysis' }}
          </p>
        </div>
        <div class="flex items-center space-x-2">
          <button 
            @click="store.downloadAudio()"
            class="p-2 text-[#6b6b73] hover:text-[#d4a55a] hover:bg-[#d4a55a]/10 rounded-lg transition-colors"
            title="Download audio"
          >
            <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
            </svg>
          </button>
          <button 
            @click="store.reset()"
            class="p-2 text-[#6b6b73] hover:text-red-400 hover:bg-red-900/20 rounded-lg transition-colors"
            title="Clear"
          >
            <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>
      </div>
      
      <!-- Settings -->
      <div class="grid md:grid-cols-2 gap-6">
        <!-- Instrument Selection -->
        <div>
          <label class="block text-sm font-medium text-[#a0a0a8] mb-3">Instrument Type</label>
          <div class="grid grid-cols-3 gap-2">
            <button
              v-for="inst in instruments"
              :key="inst.value"
              @click="store.instrument = inst.value"
              :class="[
                'p-3 rounded-xl border transition-all text-center cursor-pointer',
                store.instrument === inst.value
                  ? 'border-[#d4a55a] bg-[#d4a55a]/10 text-[#d4a55a]'
                  : 'border-[#3a3a42] hover:border-[#4a4a52] text-[#a0a0a8] hover:text-[#f5f5f5]'
              ]"
            >
              <svg class="w-6 h-6 mx-auto mb-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" :d="inst.icon" />
              </svg>
              <span class="text-xs font-medium">{{ inst.label }}</span>
            </button>
          </div>
        </div>
        
        <!-- Tempo & Time Signature -->
        <div class="space-y-4">
          <div>
            <label class="block text-sm font-medium text-[#a0a0a8] mb-2">
              Tempo (BPM)
              <span v-if="store.tempoInfo" class="text-xs text-[#d4a55a] ml-1">(auto-detected)</span>
            </label>
            <input 
              type="number" 
              v-model.number="store.tempo" 
              min="20" 
              max="300" 
              class="w-full px-4 py-2.5 bg-[#333338] border border-[#3a3a42] rounded-lg text-[#f5f5f5] focus:border-[#d4a55a] focus:ring-1 focus:ring-[#d4a55a] transition-colors"
            />
            <p v-if="store.tempoInfo?.is_variable" class="text-xs text-amber-500 mt-1">
              Variable tempo: {{ store.tempoInfo.tempo_range[0] }}-{{ store.tempoInfo.tempo_range[1] }} BPM
            </p>
          </div>
          <div>
            <label class="block text-sm font-medium text-[#a0a0a8] mb-2">
              Time Signature
              <span v-if="store.timeSignatureInfo" class="text-xs text-[#d4a55a] ml-1">(auto-detected)</span>
            </label>
            <select v-model="store.timeSignature" class="w-full px-4 py-2.5 bg-[#333338] border border-[#3a3a42] rounded-lg text-[#f5f5f5] focus:border-[#d4a55a] focus:ring-1 focus:ring-[#d4a55a] transition-colors">
              <option value="4/4">4/4</option>
              <option value="3/4">3/4</option>
              <option value="6/8">6/8</option>
              <option value="2/4">2/4</option>
            </select>
          </div>
        </div>
      </div>
      
      <!-- Title -->
      <div>
        <label class="block text-sm font-medium text-[#a0a0a8] mb-2">Song Title</label>
        <input 
          type="text" 
          v-model="store.title" 
          placeholder="Enter song title"
          class="w-full px-4 py-2.5 bg-[#333338] border border-[#3a3a42] rounded-lg text-[#f5f5f5] placeholder-[#6b6b73] focus:border-[#d4a55a] focus:ring-1 focus:ring-[#d4a55a] transition-colors"
        />
      </div>
      
      <!-- Action Buttons -->
      <div class="flex flex-wrap gap-3 pt-2">
        <button 
          @click="store.analyzeAudio()" 
          :disabled="store.isLoading"
          class="px-6 py-3 bg-[#d4a55a] text-[#1a1a1f] rounded-xl font-semibold hover:bg-[#e5b86b] transition-colors flex items-center gap-2 cursor-pointer disabled:opacity-50 shadow-lg shadow-[#d4a55a]/10"
        >
          <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4" />
          </svg>
          Full Analysis
        </button>
        
        <button 
          @click="store.detectChordsOnly()" 
          :disabled="store.isLoading"
          class="px-6 py-3 bg-[#333338] text-[#a0a0a8] rounded-xl font-medium hover:bg-[#3a3a42] hover:text-[#f5f5f5] transition-colors flex items-center gap-2 cursor-pointer disabled:opacity-50 border border-[#3a3a42]"
        >
          <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
          </svg>
          Chords Only
        </button>
      </div>
      
      <!-- Results Summary -->
      <div v-if="store.hasAnalysis" class="space-y-4 pt-6 border-t border-[#3a3a42]">
        <div class="grid grid-cols-3 gap-4">
          <div class="p-4 bg-[#333338]/50 rounded-xl border border-[#3a3a42]">
            <p class="text-sm text-[#6b6b73] mb-1">Detected Key</p>
            <p class="text-2xl font-bold text-[#d4a55a]">{{ store.detectedKey || '—' }}</p>
          </div>
          <div class="p-4 bg-[#333338]/50 rounded-xl border border-[#3a3a42]">
            <p class="text-sm text-[#6b6b73] mb-1">Chords Found</p>
            <p class="text-2xl font-bold text-[#f5f5f5]">{{ store.chords?.chords?.length || 0 }}</p>
          </div>
          <div class="p-4 bg-[#333338]/50 rounded-xl border border-[#3a3a42]">
            <p class="text-sm text-[#6b6b73] mb-1">Notes Detected</p>
            <p class="text-2xl font-bold text-[#f5f5f5]">{{ store.notes?.notes?.length || 0 }}</p>
          </div>
        </div>
        
        <div v-if="store.tempoInfo || store.timeSignatureInfo" class="grid grid-cols-2 gap-4">
          <div v-if="store.tempoInfo" class="p-4 bg-[#333338]/50 rounded-xl border border-[#3a3a42]">
            <p class="text-sm text-[#6b6b73] mb-1">Detected Tempo</p>
            <p class="text-xl font-bold text-[#f5f5f5]">{{ store.tempoInfo.tempo }} <span class="text-sm text-[#6b6b73]">BPM</span></p>
            <p class="text-xs text-[#6b6b73] mt-1">{{ Math.round(store.tempoInfo.confidence * 100) }}% confidence</p>
          </div>
          <div v-if="store.timeSignatureInfo" class="p-4 bg-[#333338]/50 rounded-xl border border-[#3a3a42]">
            <p class="text-sm text-[#6b6b73] mb-1">Time Signature</p>
            <p class="text-xl font-bold text-[#f5f5f5]">{{ store.timeSignatureInfo.time_signature }}</p>
            <p class="text-xs text-[#6b6b73] mt-1">{{ Math.round(store.timeSignatureInfo.confidence * 100) }}% confidence</p>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
