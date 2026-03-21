<script setup>
import { ref, watch, onMounted, nextTick } from 'vue'
import { useAudioStore } from '../stores/audio'

const store = useAudioStore()
const sheetContainer = ref(null)
const osmd = ref(null)

const outputTypes = [
  { value: 'chords_only', label: 'Chords Only' },
  { value: 'lead_sheet', label: 'Lead Sheet' },
  { value: 'full_score', label: 'Full Score' },
]

const selectedType = ref('lead_sheet')

const loadError = ref(null)
const xmlBlobUrl = ref(null)
const isRendering = ref(false)
const debugInfo = ref(null)
const pendingRender = ref(false)

const loadOSMD = async () => {
  debugInfo.value = 'Starting loadOSMD...'
  
  // Wait for next tick to ensure DOM is ready
  await nextTick()
  
  if (!sheetContainer.value) {
    debugInfo.value = 'Container not ready, will retry when mounted...'
    pendingRender.value = true
    return
  }
  
  if (!store.sheet?.content) {
    debugInfo.value = 'Error: No sheet content available'
    return
  }
  
  pendingRender.value = false
  loadError.value = null
  isRendering.value = true
  
  // Clean up previous blob URL
  if (xmlBlobUrl.value) {
    URL.revokeObjectURL(xmlBlobUrl.value)
    xmlBlobUrl.value = null
  }
  
  try {
    debugInfo.value = `Content length: ${store.sheet.content.length} chars. Loading OSMD...`
    
    const { OpenSheetMusicDisplay } = await import('opensheetmusicdisplay')
    
    // Clear previous content
    sheetContainer.value.innerHTML = ''
    
    osmd.value = new OpenSheetMusicDisplay(sheetContainer.value, {
      autoResize: true,
      backend: 'svg',
      drawTitle: true,
      drawComposer: true,
      drawingParameters: 'default',
    })
    
    // Get the MusicXML content
    let xmlContent = store.sheet.content
    
    // Remove BOM if present
    if (xmlContent.charCodeAt(0) === 0xFEFF) {
      xmlContent = xmlContent.slice(1)
    }
    
    // Log first 200 chars for debugging
    const preview = xmlContent.substring(0, 150)
    console.log('MusicXML content preview:', preview)
    debugInfo.value = `XML preview: ${preview.substring(0, 80)}...`
    
    // Create a Blob URL from the XML content
    const blob = new Blob([xmlContent], { type: 'application/xml' })
    xmlBlobUrl.value = URL.createObjectURL(blob)
    
    debugInfo.value = 'Loading XML into OSMD...'
    
    // Load via URL - this often works better than raw string
    await osmd.value.load(xmlBlobUrl.value)
    
    debugInfo.value = 'Rendering...'
    
    // Wait a tick before rendering to ensure load is complete
    await nextTick()
    
    if (osmd.value && osmd.value.IsReadyToRender()) {
      osmd.value.render()
    }
    
    debugInfo.value = null // Clear debug on success
    isRendering.value = false
  } catch (e) {
    console.error('Failed to render sheet music:', e)
    loadError.value = `Failed to render: ${e.message}`
    debugInfo.value = `Error: ${e.message}`
    isRendering.value = false
  }
}

watch(() => store.sheet?.content, (newContent) => {
  console.log('Sheet content changed, length:', newContent?.length)
  if (newContent) {
    loadOSMD()
  }
})

// Watch for when the container becomes available
watch(sheetContainer, (newVal) => {
  if (newVal && (pendingRender.value || store.sheet?.content)) {
    console.log('Container now available, rendering...')
    loadOSMD()
  }
})

onMounted(() => {
  console.log('SheetViewer mounted, sheet content:', store.sheet?.content?.length)
  if (store.sheet?.content) {
    loadOSMD()
  }
})
</script>

<template>
  <div class="space-y-6">
    <!-- Controls -->
    <div class="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
      <h2 class="text-xl font-semibold text-gray-900 mb-6">Sheet Music</h2>
      
      <div v-if="!store.hasFile" class="text-center py-8">
        <p class="text-gray-500">Upload and analyze an audio file first</p>
      </div>
      
      <div v-else class="space-y-4">
        <!-- Output Type Selection -->
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">Output Type</label>
          <div class="flex flex-wrap gap-2">
            <button
              v-for="type in outputTypes"
              :key="type.value"
              @click="selectedType = type.value"
              :class="[
                'px-4 py-2 rounded-lg border-2 transition-all text-sm font-medium cursor-pointer',
                selectedType === type.value
                  ? 'border-sky-500 bg-sky-50 text-sky-700'
                  : 'border-gray-200 hover:border-gray-300 text-gray-600'
              ]"
            >
              {{ type.label }}
            </button>
          </div>
        </div>
        
        <!-- Rhythm Correction Strength -->
        <div>
          <div class="flex items-center justify-between mb-1">
            <label class="block text-sm font-medium text-gray-700">
              Rhythm Correction
            </label>
            <span class="text-sm text-gray-500">
              {{ store.correctionStrength === 0 ? 'Off' : Math.round(store.correctionStrength * 100) + '%' }}
            </span>
          </div>
          <input 
            type="range" 
            v-model.number="store.correctionStrength" 
            min="0" 
            max="1" 
            step="0.1"
            class="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-sky-600"
          />
          <div class="flex justify-between text-xs text-gray-400 mt-1">
            <span>Off</span>
            <span>Light</span>
            <span>Medium</span>
            <span>Strong</span>
            <span>Max</span>
          </div>
          <p class="text-xs text-gray-500 mt-2">
            Higher values apply more aggressive timing and duration corrections based on learned patterns.
          </p>
        </div>
        
        <!-- Generate Button -->
        <div class="flex flex-wrap gap-3">
          <button 
            @click="store.generateSheetMusic(selectedType)"
            :disabled="store.isLoading || !store.hasFile"
            class="px-4 py-2 bg-sky-600 text-white rounded-lg font-medium hover:bg-sky-700 transition-colors flex items-center space-x-2 cursor-pointer disabled:opacity-50"
          >
            <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
            <span>Generate Sheet Music</span>
          </button>
          
          <button 
            @click="store.generateMelodySuggestion('simple')"
            :disabled="store.isLoading || !store.hasFile"
            class="px-4 py-2 bg-fuchsia-600 text-white rounded-lg font-medium hover:bg-fuchsia-700 transition-colors flex items-center space-x-2 cursor-pointer disabled:opacity-50"
          >
            <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 19V6l12-3v13M9 19c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zm12-3c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zM9 10l12-3" />
            </svg>
            <span>Suggest Melody</span>
          </button>
        </div>
      </div>
    </div>
    
    <!-- Sheet Music Display -->
    <div v-if="store.sheet?.content" class="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
      <div class="flex items-center justify-between mb-4">
        <h3 class="font-semibold text-gray-900">Generated Sheet Music</h3>
        <div class="flex gap-2">
          <button @click="store.downloadMusicXML()" class="px-4 py-2 bg-gray-200 text-gray-800 rounded-lg font-medium text-sm hover:bg-gray-300 transition-colors cursor-pointer">
            Download MusicXML
          </button>
          <button 
            v-if="store.midiBase64" 
            @click="store.downloadMidi()" 
            class="px-4 py-2 bg-gray-200 text-gray-800 rounded-lg font-medium text-sm hover:bg-gray-300 transition-colors cursor-pointer"
          >
            Download MIDI
          </button>
        </div>
      </div>
      
      <div v-if="loadError" class="p-4 bg-red-50 border border-red-200 rounded-lg text-red-700 mb-4">
        {{ loadError }}
      </div>
      
      <div v-if="isRendering" class="p-4 bg-blue-50 border border-blue-200 rounded-lg text-blue-700 mb-4">
        Rendering sheet music...
      </div>
      
      <div v-if="debugInfo" class="p-4 bg-gray-50 border border-gray-200 rounded-lg text-gray-700 mb-4 text-xs font-mono">
        <p><strong>Debug:</strong> {{ debugInfo }}</p>
      </div>
      
      <div 
        ref="sheetContainer" 
        class="bg-white border border-gray-200 rounded-lg p-4 min-h-[400px]"
      ></div>
    </div>
    
    <!-- Melody Suggestion -->
    <div v-if="store.melody" class="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
      <div class="flex items-center justify-between mb-4">
        <h3 class="font-semibold text-gray-900">Suggested Melody</h3>
        <button @click="store.downloadMidi()" class="px-4 py-2 bg-gray-200 text-gray-800 rounded-lg font-medium text-sm hover:bg-gray-300 transition-colors cursor-pointer">
          Download MIDI
        </button>
      </div>
      
      <div class="p-4 bg-fuchsia-50 rounded-lg">
        <p class="text-sm text-fuchsia-700 mb-2">
          Generated {{ store.melody?.notes?.length || 0 }} notes
        </p>
        <p class="text-xs text-fuchsia-600">
          Download the MIDI file to hear the suggested melody
        </p>
      </div>
    </div>
  </div>
</template>
