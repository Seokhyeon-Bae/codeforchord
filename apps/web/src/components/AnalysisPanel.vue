<script setup>
import { useAudioStore } from '../stores/audio'

const store = useAudioStore()

const instruments = [
  { value: 'piano', label: 'Piano', icon: '🎹' },
  { value: 'guitar', label: 'Guitar', icon: '🎸' },
  { value: 'vocal', label: 'Vocal', icon: '🎤' },
]
</script>

<template>
  <div class="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
    <h2 class="text-xl font-semibold text-gray-900 mb-6">Audio Analysis</h2>
    
    <!-- No File Warning -->
    <div v-if="!store.hasFile" class="text-center py-8">
      <div class="w-16 h-16 bg-gray-100 rounded-full flex items-center justify-center mx-auto mb-4">
        <svg class="w-8 h-8 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 19V6l12-3v13M9 19c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zm12-3c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zM9 10l12-3" />
        </svg>
      </div>
      <p class="text-gray-500">Upload an audio file first to analyze</p>
    </div>
    
    <!-- Analysis Controls -->
    <div v-else class="space-y-6">
      <!-- File Info -->
      <div class="flex items-center p-4 bg-gray-50 rounded-lg">
        <div class="w-12 h-12 bg-sky-100 rounded-lg flex items-center justify-center mr-4">
          <svg class="w-6 h-6 text-sky-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 19V6l12-3v13M9 19c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zm12-3c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zM9 10l12-3" />
          </svg>
        </div>
        <div class="flex-1">
          <p class="font-medium text-gray-900">{{ store.fileName }}</p>
          <p class="text-sm text-gray-500">Ready for analysis</p>
        </div>
      </div>
      
      <!-- Settings -->
      <div class="grid md:grid-cols-2 gap-4">
        <!-- Instrument Selection -->
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">Instrument Type</label>
          <div class="grid grid-cols-3 gap-2">
            <button
              v-for="inst in instruments"
              :key="inst.value"
              @click="store.instrument = inst.value"
              :class="[
                'p-3 rounded-lg border-2 transition-all text-center cursor-pointer',
                store.instrument === inst.value
                  ? 'border-sky-500 bg-sky-50'
                  : 'border-gray-200 hover:border-gray-300'
              ]"
            >
              <span class="text-2xl block mb-1">{{ inst.icon }}</span>
              <span class="text-sm font-medium">{{ inst.label }}</span>
            </button>
          </div>
        </div>
        
        <!-- Tempo & Time Signature -->
        <div class="space-y-4">
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">
              Tempo (BPM)
              <span v-if="store.tempoInfo" class="text-xs text-green-600 ml-1">
                (auto-detected)
              </span>
            </label>
            <input 
              type="number" 
              v-model.number="store.tempo" 
              min="20" 
              max="300" 
              class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-sky-500 focus:border-sky-500 transition-colors"
            />
            <p v-if="store.tempoInfo?.is_variable" class="text-xs text-amber-600 mt-1">
              ⚠️ Variable tempo detected ({{ store.tempoInfo.tempo_range[0] }}-{{ store.tempoInfo.tempo_range[1] }} BPM)
            </p>
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">
              Time Signature
              <span v-if="store.timeSignatureInfo" class="text-xs text-green-600 ml-1">
                (auto-detected)
              </span>
            </label>
            <select v-model="store.timeSignature" class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-sky-500 focus:border-sky-500 transition-colors">
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
        <label class="block text-sm font-medium text-gray-700 mb-1">Song Title</label>
        <input 
          type="text" 
          v-model="store.title" 
          placeholder="Enter song title"
          class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-sky-500 focus:border-sky-500 transition-colors"
        />
      </div>
      
      <!-- Action Buttons -->
      <div class="flex flex-wrap gap-3">
        <button 
          @click="store.analyzeAudio()" 
          :disabled="store.isLoading"
          class="px-4 py-2 bg-sky-600 text-white rounded-lg font-medium hover:bg-sky-700 transition-colors flex items-center space-x-2 cursor-pointer disabled:opacity-50"
        >
          <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4" />
          </svg>
          <span>Full Analysis</span>
        </button>
        
        <button 
          @click="store.detectChordsOnly()" 
          :disabled="store.isLoading"
          class="px-4 py-2 bg-gray-200 text-gray-800 rounded-lg font-medium hover:bg-gray-300 transition-colors flex items-center space-x-2 cursor-pointer disabled:opacity-50"
        >
          <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
          </svg>
          <span>Chords Only</span>
        </button>
      </div>
      
      <!-- Results Summary -->
      <div v-if="store.hasAnalysis" class="space-y-4 pt-6 border-t border-gray-200">
        <div class="grid md:grid-cols-3 gap-4">
          <div class="p-4 bg-green-50 rounded-lg">
            <p class="text-sm text-green-600 font-medium">Detected Key</p>
            <p class="text-2xl font-bold text-green-700">{{ store.detectedKey || 'Unknown' }}</p>
          </div>
          <div class="p-4 bg-blue-50 rounded-lg">
            <p class="text-sm text-blue-600 font-medium">Chords Found</p>
            <p class="text-2xl font-bold text-blue-700">{{ store.chords?.chords?.length || 0 }}</p>
          </div>
          <div class="p-4 bg-purple-50 rounded-lg">
            <p class="text-sm text-purple-600 font-medium">Notes Detected</p>
            <p class="text-2xl font-bold text-purple-700">{{ store.notes?.notes?.length || 0 }}</p>
          </div>
        </div>
        
        <!-- Tempo & Time Signature Detection Results -->
        <div v-if="store.tempoInfo || store.timeSignatureInfo" class="grid md:grid-cols-2 gap-4">
          <div v-if="store.tempoInfo" class="p-4 bg-amber-50 rounded-lg">
            <p class="text-sm text-amber-600 font-medium">Detected Tempo</p>
            <p class="text-2xl font-bold text-amber-700">{{ store.tempoInfo.tempo }} BPM</p>
            <p class="text-xs text-amber-600 mt-1">
              Confidence: {{ Math.round(store.tempoInfo.confidence * 100) }}%
              <span v-if="store.tempoInfo.is_variable" class="ml-2">(Variable)</span>
            </p>
          </div>
          <div v-if="store.timeSignatureInfo" class="p-4 bg-cyan-50 rounded-lg">
            <p class="text-sm text-cyan-600 font-medium">Detected Time Signature</p>
            <p class="text-2xl font-bold text-cyan-700">{{ store.timeSignatureInfo.time_signature }}</p>
            <p class="text-xs text-cyan-600 mt-1">
              Confidence: {{ Math.round(store.timeSignatureInfo.confidence * 100) }}%
            </p>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
