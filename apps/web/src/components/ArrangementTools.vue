<script setup>
import { ref } from 'vue'
import { useAudioStore } from '../stores/audio'

const store = useAudioStore()

const transposeValue = ref(0)

const transposeOptions = [
  { value: -6, label: '-6 (Tritone down)' },
  { value: -5, label: '-5' },
  { value: -4, label: '-4' },
  { value: -3, label: '-3 (Minor 3rd down)' },
  { value: -2, label: '-2 (Whole step down)' },
  { value: -1, label: '-1 (Half step down)' },
  { value: 0, label: '0 (Original)' },
  { value: 1, label: '+1 (Half step up)' },
  { value: 2, label: '+2 (Whole step up)' },
  { value: 3, label: '+3 (Minor 3rd up)' },
  { value: 4, label: '+4' },
  { value: 5, label: '+5' },
  { value: 6, label: '+6 (Tritone up)' },
]

const melodyStyles = [
  { value: 'simple', label: 'Simple', desc: 'Basic chord tones' },
  { value: 'arpeggiated', label: 'Arpeggiated', desc: 'Broken chord patterns' },
  { value: 'scalar', label: 'Scalar', desc: 'Scale-based motion' },
  { value: 'rhythmic', label: 'Rhythmic', desc: 'Syncopated patterns' },
]

const selectedMelodyStyle = ref('simple')
</script>

<template>
  <div class="space-y-6">
    <!-- Main Card -->
    <div class="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
      <h2 class="text-xl font-semibold text-gray-900 mb-6">Arrangement Tools</h2>
      
      <div v-if="!store.hasFile" class="text-center py-8">
        <p class="text-gray-500">Upload and analyze an audio file first</p>
      </div>
      
      <div v-else class="space-y-8">
        <!-- Transpose Section -->
        <div>
          <h3 class="font-medium text-gray-900 mb-3 flex items-center">
            <svg class="w-5 h-5 mr-2 text-sky-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 16V4m0 0L3 8m4-4l4 4m6 0v12m0 0l4-4m-4 4l-4-4" />
            </svg>
            Transpose
          </h3>
          <p class="text-sm text-gray-500 mb-4">Shift all notes and chords up or down</p>
          
          <div class="flex flex-wrap items-end gap-4">
            <div class="flex-1 min-w-[200px]">
              <label class="block text-sm font-medium text-gray-700 mb-1">Semitones</label>
              <select v-model="transposeValue" class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-sky-500 focus:border-sky-500 transition-colors">
                <option v-for="opt in transposeOptions" :key="opt.value" :value="opt.value">
                  {{ opt.label }}
                </option>
              </select>
            </div>
            <button 
              @click="store.transposeMusic(transposeValue)"
              :disabled="store.isLoading || transposeValue === 0"
              class="px-4 py-2 bg-sky-600 text-white rounded-lg font-medium hover:bg-sky-700 transition-colors cursor-pointer disabled:opacity-50"
            >
              Apply Transpose
            </button>
          </div>
        </div>
        
        <!-- Mode Conversion Section -->
        <div class="pt-6 border-t border-gray-200">
          <h3 class="font-medium text-gray-900 mb-3 flex items-center">
            <svg class="w-5 h-5 mr-2 text-sky-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 7h12m0 0l-4-4m4 4l-4 4m0 6H4m0 0l4 4m-4-4l4-4" />
            </svg>
            Mode Conversion
          </h3>
          <p class="text-sm text-gray-500 mb-4">Convert between major and minor modes</p>
          
          <div class="flex flex-wrap gap-3">
            <button 
              @click="store.convertToMode('minor')"
              :disabled="store.isLoading"
              class="px-4 py-2 bg-gray-200 text-gray-800 rounded-lg font-medium hover:bg-gray-300 transition-colors flex items-center space-x-2 cursor-pointer disabled:opacity-50"
            >
              <span>Major → Minor</span>
            </button>
            <button 
              @click="store.convertToMode('major')"
              :disabled="store.isLoading"
              class="px-4 py-2 bg-gray-200 text-gray-800 rounded-lg font-medium hover:bg-gray-300 transition-colors flex items-center space-x-2 cursor-pointer disabled:opacity-50"
            >
              <span>Minor → Major</span>
            </button>
          </div>
        </div>
        
        <!-- Simplification Section -->
        <div class="pt-6 border-t border-gray-200">
          <h3 class="font-medium text-gray-900 mb-3 flex items-center">
            <svg class="w-5 h-5 mr-2 text-sky-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z" />
            </svg>
            Chord Simplification
          </h3>
          <p class="text-sm text-gray-500 mb-4">Simplify complex chords for easier playing</p>
          
          <div class="flex flex-wrap gap-3">
            <button 
              @click="store.simplify()"
              :disabled="store.isLoading"
              class="px-4 py-2 bg-gray-200 text-gray-800 rounded-lg font-medium hover:bg-gray-300 transition-colors cursor-pointer disabled:opacity-50"
            >
              Simplify for {{ store.instrument === 'guitar' ? 'Guitar' : 'Easy Play' }}
            </button>
          </div>
        </div>
        
        <!-- Melody Suggestion Section -->
        <div class="pt-6 border-t border-gray-200">
          <h3 class="font-medium text-gray-900 mb-3 flex items-center">
            <svg class="w-5 h-5 mr-2 text-fuchsia-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 19V6l12-3v13M9 19c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zm12-3c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zM9 10l12-3" />
            </svg>
            Melody Suggestion
          </h3>
          <p class="text-sm text-gray-500 mb-4">Generate a melody based on detected chords</p>
          
          <div class="grid grid-cols-2 md:grid-cols-4 gap-3 mb-4">
            <button
              v-for="style in melodyStyles"
              :key="style.value"
              @click="selectedMelodyStyle = style.value"
              :class="[
                'p-3 rounded-lg border-2 text-left transition-all cursor-pointer',
                selectedMelodyStyle === style.value
                  ? 'border-fuchsia-500 bg-fuchsia-50'
                  : 'border-gray-200 hover:border-gray-300'
              ]"
            >
              <p class="font-medium text-sm">{{ style.label }}</p>
              <p class="text-xs text-gray-500">{{ style.desc }}</p>
            </button>
          </div>
          
          <button 
            @click="store.generateMelodySuggestion(selectedMelodyStyle)"
            :disabled="store.isLoading"
            class="px-4 py-2 bg-fuchsia-600 text-white rounded-lg font-medium hover:bg-fuchsia-700 transition-colors cursor-pointer disabled:opacity-50"
          >
            Generate Melody
          </button>
        </div>
      </div>
    </div>
    
    <!-- Results Preview -->
    <div v-if="store.chords && store.hasAnalysis" class="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
      <h3 class="font-semibold text-gray-900 mb-4">Current Chord Progression</h3>
      <div class="flex flex-wrap gap-2">
        <span
          v-for="(chord, i) in store.chords?.chords?.slice(0, 16)"
          :key="i"
          class="px-3 py-1.5 bg-sky-100 text-sky-800 rounded-lg text-sm font-semibold"
        >
          {{ chord.symbol }}
        </span>
        <span 
          v-if="store.chords?.chords?.length > 16" 
          class="px-3 py-1.5 bg-gray-100 text-gray-600 rounded-lg text-sm"
        >
          +{{ store.chords.chords.length - 16 }} more
        </span>
      </div>
    </div>
  </div>
</template>
