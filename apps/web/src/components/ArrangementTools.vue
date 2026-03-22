<script setup>
import { ref } from 'vue'
import { useAudioStore } from '../stores/audio'

const store = useAudioStore()

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
    <div class="bg-[#2a2a30]/80 backdrop-blur-sm rounded-xl border border-[#3a3a42] p-6">
      <h2 class="text-xl font-bold text-[#f5f5f5] mb-6">Arrangement Tools</h2>
      
      <div v-if="!store.hasFile" class="text-center py-12">
        <div class="w-20 h-20 bg-[#333338] rounded-full flex items-center justify-center mx-auto mb-4">
          <svg class="w-10 h-10 text-[#6b6b73]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 6V4m0 2a2 2 0 100 4m0-4a2 2 0 110 4m-6 8a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4m6 6v10m6-2a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4" />
          </svg>
        </div>
        <p class="text-[#6b6b73]">Upload and analyze an audio file first</p>
      </div>
      
      <div v-else class="space-y-8">
        <!-- Mode Conversion Section -->
        <div>
          <h3 class="font-medium text-[#f5f5f5] mb-3 flex items-center">
            <svg class="w-5 h-5 mr-2 text-[#d4a55a]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 7h12m0 0l-4-4m4 4l-4 4m0 6H4m0 0l4 4m-4-4l4-4" />
            </svg>
            Mode Conversion
          </h3>
          <p class="text-sm text-[#6b6b73] mb-4">Convert between major and minor modes using music theory rules</p>
          
          <!-- Available when chords detected in Chords Only mode -->
          <div v-if="store.chords && (!store.notes || store.notes?.notes?.length === 0)">
            <div class="p-4 bg-[#333338]/50 rounded-xl border border-[#3a3a42] mb-4">
              <p class="text-sm text-[#a0a0a8] mb-3">
                <strong class="text-[#f5f5f5]">Parallel Mode Conversion:</strong>
              </p>
              <ul class="text-xs text-[#6b6b73] space-y-1 ml-4 list-disc">
                <li><span class="text-[#d4a55a]">Major → Minor:</span> C → Cm, Cmaj7 → Cm7, C7 → Cm7</li>
                <li><span class="text-[#d4a55a]">Minor → Major:</span> Cm → C, Cm7 → Cmaj7, Cdim → C</li>
              </ul>
            </div>
            
            <div class="flex flex-wrap gap-3">
              <button 
                @click="store.convertToMode('minor')"
                :disabled="store.isLoading"
                class="px-6 py-3 bg-[#d4a55a] text-[#1a1a1f] rounded-xl font-semibold hover:bg-[#e5b86b] transition-colors cursor-pointer disabled:opacity-50"
              >
                Major → Minor
              </button>
              <button 
                @click="store.convertToMode('major')"
                :disabled="store.isLoading"
                class="px-6 py-3 bg-[#333338] text-[#f5f5f5] rounded-xl font-semibold hover:bg-[#3a3a42] transition-colors cursor-pointer disabled:opacity-50 border border-[#3a3a42]"
              >
                Minor → Major
              </button>
            </div>
            
            <p class="text-xs text-[#6b6b73] mt-3">
              After conversion, go to Sheet tab and regenerate to see the new chords.
            </p>
          </div>
          
          <!-- Message when notes are detected (Full Analysis mode) -->
          <div v-else-if="store.notes && store.notes?.notes?.length > 0" class="p-4 bg-[#333338]/50 rounded-xl border border-[#3a3a42]">
            <p class="text-[#a0a0a8] text-sm">
              <strong class="text-[#f5f5f5]">Mode conversion is only available in "Chords Only" mode.</strong>
              <br/><br/>
              To use mode conversion, run "Chords Only" analysis instead of "Full Analysis".
            </p>
          </div>
          
          <!-- No chords detected -->
          <div v-else class="p-4 bg-[#333338]/50 rounded-xl border border-[#3a3a42]">
            <p class="text-[#6b6b73] text-sm">Detect chords first using "Chords Only" analysis to enable mode conversion.</p>
          </div>
        </div>
        
        <!-- Melody Suggestion Section -->
        <div class="pt-6 border-t border-[#3a3a42]">
          <h3 class="font-medium text-[#f5f5f5] mb-3 flex items-center">
            <svg class="w-5 h-5 mr-2 text-[#d4a55a]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 19V6l12-3v13M9 19c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zm12-3c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zM9 10l12-3" />
            </svg>
            Melody Suggestion
          </h3>
          <p class="text-sm text-[#6b6b73] mb-4">Generate a melody based on detected chords</p>
          
          <!-- Only available in Chords Only mode -->
          <div v-if="store.chords && (!store.notes || store.notes?.notes?.length === 0)">
            <div class="grid grid-cols-2 md:grid-cols-4 gap-3 mb-4">
              <button
                v-for="style in melodyStyles"
                :key="style.value"
                @click="selectedMelodyStyle = style.value"
                :class="[
                  'p-3 rounded-xl border text-left transition-all cursor-pointer',
                  selectedMelodyStyle === style.value
                    ? 'border-[#d4a55a] bg-[#d4a55a]/10'
                    : 'border-[#3a3a42] hover:border-[#4a4a52]'
                ]"
              >
                <p :class="['font-medium text-sm', selectedMelodyStyle === style.value ? 'text-[#d4a55a]' : 'text-[#a0a0a8]']">{{ style.label }}</p>
                <p class="text-xs text-[#6b6b73]">{{ style.desc }}</p>
              </button>
            </div>
            
            <button 
              @click="store.generateMelodySuggestion(selectedMelodyStyle)"
              :disabled="store.isLoading || !store.chords"
              class="px-6 py-2.5 bg-[#d4a55a] text-[#1a1a1f] rounded-lg font-semibold hover:bg-[#e5b86b] transition-colors cursor-pointer disabled:opacity-50"
            >
              Generate Melody
            </button>
          </div>
          
          <!-- Show message when notes are detected (Full Analysis mode) -->
          <div v-else-if="store.notes && store.notes?.notes?.length > 0" class="p-4 bg-[#333338]/50 rounded-xl border border-[#3a3a42]">
            <p class="text-[#a0a0a8] text-sm">
              <strong class="text-[#f5f5f5]">Melody suggestion is only available in "Chords Only" mode.</strong>
              <br/><br/>
              Since notes were already detected from your audio, use them as the melody instead.
              To use melody suggestion, run "Chords Only" analysis.
            </p>
          </div>
          
          <!-- No chords detected -->
          <div v-else class="p-4 bg-[#333338]/50 rounded-xl border border-[#3a3a42]">
            <p class="text-[#6b6b73] text-sm">Detect chords first using "Chords Only" mode to generate melody suggestions.</p>
          </div>
        </div>
      </div>
    </div>
    
    <!-- Results Preview -->
    <div v-if="store.chords && store.hasAnalysis" class="bg-[#2a2a30]/80 backdrop-blur-sm rounded-xl border border-[#3a3a42] p-6">
      <h3 class="font-semibold text-[#f5f5f5] mb-4">Current Chord Progression</h3>
      <div class="flex flex-wrap gap-2">
        <span
          v-for="(chord, i) in store.chords?.chords?.slice(0, 16)"
          :key="i"
          class="px-3 py-1.5 bg-[#d4a55a]/15 text-[#d4a55a] rounded-lg text-sm font-semibold border border-[#d4a55a]/20"
        >
          {{ chord.symbol }}
        </span>
        <span 
          v-if="store.chords?.chords?.length > 16" 
          class="px-3 py-1.5 bg-[#333338] text-[#6b6b73] rounded-lg text-sm border border-[#3a3a42]"
        >
          +{{ store.chords.chords.length - 16 }} more
        </span>
      </div>
    </div>
  </div>
</template>
