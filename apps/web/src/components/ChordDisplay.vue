<script setup>
import { computed } from 'vue'
import { useAudioStore } from '../stores/audio'

const store = useAudioStore()

const chordColors = {
  'C': 'bg-red-100 text-red-800',
  'D': 'bg-orange-100 text-orange-800',
  'E': 'bg-yellow-100 text-yellow-800',
  'F': 'bg-green-100 text-green-800',
  'G': 'bg-teal-100 text-teal-800',
  'A': 'bg-blue-100 text-blue-800',
  'B': 'bg-purple-100 text-purple-800',
}

const getChordColor = (symbol) => {
  const root = symbol.charAt(0).toUpperCase()
  return chordColors[root] || 'bg-gray-100 text-gray-800'
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
  <div class="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
    <div class="flex items-center justify-between mb-6">
      <h3 class="text-lg font-semibold text-gray-900">Detected Chords</h3>
      <span class="text-sm text-gray-500">
        {{ store.chords?.chords?.length || 0 }} chord changes
      </span>
    </div>
    
    <!-- Unique Chords Summary -->
    <div class="mb-6">
      <p class="text-sm text-gray-600 mb-2">Unique chords in this piece:</p>
      <div class="flex flex-wrap gap-2">
        <span
          v-for="chord in uniqueChords"
          :key="chord.symbol"
          :class="['inline-flex items-center px-3 py-1 rounded-full text-sm font-semibold', getChordColor(chord.symbol)]"
        >
          {{ chord.symbol }}
        </span>
      </div>
    </div>
    
    <!-- Timeline -->
    <div class="space-y-2 max-h-64 overflow-y-auto">
      <div
        v-for="(chord, index) in store.chords?.chords"
        :key="index"
        class="flex items-center p-3 bg-gray-50 rounded-lg hover:bg-gray-100 transition-colors"
      >
        <span class="text-sm text-gray-500 w-16 font-mono">
          {{ formatTime(chord.timestamp) }}
        </span>
        <span :class="['inline-flex items-center px-3 py-1 rounded-full text-sm font-semibold ml-2', getChordColor(chord.symbol)]">
          {{ chord.symbol }}
        </span>
        <span class="text-sm text-gray-400 ml-auto">
          {{ chord.duration?.toFixed(1) }}s
        </span>
      </div>
    </div>
    
    <!-- Empty State -->
    <div v-if="!store.chords?.chords?.length" class="text-center py-8">
      <p class="text-gray-500">No chords detected yet</p>
    </div>
  </div>
</template>
