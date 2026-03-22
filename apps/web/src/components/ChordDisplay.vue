<script setup>
import { computed } from 'vue'
import { useAudioStore } from '../stores/audio'

const store = useAudioStore()

const getChordColor = (symbol) => {
  const root = symbol.charAt(0).toUpperCase()
  const colors = {
    'C': 'bg-[#d4a55a]/20 text-[#d4a55a] border-[#d4a55a]/30',
    'D': 'bg-[#d4a55a]/15 text-[#e5b86b] border-[#d4a55a]/25',
    'E': 'bg-[#a8844a]/20 text-[#d4a55a] border-[#a8844a]/30',
    'F': 'bg-[#d4a55a]/10 text-[#d4a55a] border-[#d4a55a]/20',
    'G': 'bg-[#d4a55a]/20 text-[#e5b86b] border-[#d4a55a]/30',
    'A': 'bg-[#a8844a]/15 text-[#d4a55a] border-[#a8844a]/25',
    'B': 'bg-[#d4a55a]/15 text-[#d4a55a] border-[#d4a55a]/25',
  }
  return colors[root] || 'bg-[#333338] text-[#a0a0a8] border-[#3a3a42]'
}

const formatTime = (seconds) => {
  const mins = Math.floor(seconds / 60)
  const secs = Math.floor(seconds % 60)
  return `${mins}:${secs.toString().padStart(2, '0')}`
}

const uniqueChords = computed(() => {
  if (!store.chords?.chords) return []
  const seen = new Set()
  return store.chords.chords.filter(c => {
    if (seen.has(c.symbol)) return false
    seen.add(c.symbol)
    return true
  })
})
</script>

<template>
  <div class="bg-[#2a2a30]/80 backdrop-blur-sm rounded-xl border border-[#3a3a42] p-6">
    <div class="flex items-center justify-between mb-6">
      <h3 class="text-lg font-semibold text-[#f5f5f5]">Detected Chords</h3>
      <span class="text-sm text-[#6b6b73]">
        {{ store.chords?.chords?.length || 0 }} chord changes
      </span>
    </div>
    
    <!-- Unique Chords Summary -->
    <div class="mb-6">
      <p class="text-sm text-[#a0a0a8] mb-3">Unique chords in this piece:</p>
      <div class="flex flex-wrap gap-2">
        <span
          v-for="chord in uniqueChords"
          :key="chord.symbol"
          :class="['inline-flex items-center px-4 py-1.5 rounded-full text-sm font-semibold border', getChordColor(chord.symbol)]"
        >
          {{ chord.symbol }}
        </span>
      </div>
    </div>
    
    <!-- Timeline -->
    <div class="space-y-2 max-h-64 overflow-y-auto pr-2">
      <div
        v-for="(chord, index) in store.chords?.chords"
        :key="index"
        class="flex items-center p-3 bg-[#333338]/50 rounded-lg hover:bg-[#333338] transition-colors border border-[#3a3a42]/50"
      >
        <span class="text-sm text-[#6b6b73] w-16 font-mono">
          {{ formatTime(chord.timestamp) }}
        </span>
        <span :class="['inline-flex items-center px-3 py-1 rounded-full text-sm font-semibold border ml-2', getChordColor(chord.symbol)]">
          {{ chord.symbol }}
        </span>
        <span class="text-sm text-[#6b6b73] ml-auto">
          {{ chord.duration?.toFixed(1) }}s
        </span>
      </div>
    </div>
    
    <!-- Empty State -->
    <div v-if="!store.chords?.chords?.length" class="text-center py-8">
      <p class="text-[#6b6b73]">No chords detected yet</p>
    </div>
  </div>
</template>
