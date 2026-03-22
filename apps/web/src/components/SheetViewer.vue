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
  
  if (xmlBlobUrl.value) {
    URL.revokeObjectURL(xmlBlobUrl.value)
    xmlBlobUrl.value = null
  }
  
  try {
    debugInfo.value = `Content length: ${store.sheet.content.length} chars. Loading OSMD...`
    
    const { OpenSheetMusicDisplay } = await import('opensheetmusicdisplay')
    
    sheetContainer.value.innerHTML = ''
    
    osmd.value = new OpenSheetMusicDisplay(sheetContainer.value, {
      autoResize: true,
      backend: 'svg',
      drawTitle: true,
      drawComposer: true,
      drawingParameters: 'default',
    })
    
    let xmlContent = store.sheet.content
    
    if (xmlContent.charCodeAt(0) === 0xFEFF) {
      xmlContent = xmlContent.slice(1)
    }
    
    const preview = xmlContent.substring(0, 150)
    console.log('MusicXML content preview:', preview)
    debugInfo.value = `XML preview: ${preview.substring(0, 80)}...`
    
    const blob = new Blob([xmlContent], { type: 'application/xml' })
    xmlBlobUrl.value = URL.createObjectURL(blob)
    
    debugInfo.value = 'Loading XML into OSMD...'
    
    await osmd.value.load(xmlBlobUrl.value)
    
    debugInfo.value = 'Rendering...'
    
    await nextTick()
    
    if (osmd.value && osmd.value.IsReadyToRender()) {
      osmd.value.render()
    }
    
    debugInfo.value = null
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
    <div class="bg-[#2a2a30]/80 backdrop-blur-sm rounded-xl border border-[#3a3a42] p-6">
      <h2 class="text-xl font-bold text-[#f5f5f5] mb-6">Sheet Music</h2>
      
      <div v-if="!store.hasFile" class="text-center py-12">
        <div class="w-20 h-20 bg-[#333338] rounded-full flex items-center justify-center mx-auto mb-4">
          <svg class="w-10 h-10 text-[#6b6b73]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
          </svg>
        </div>
        <p class="text-[#6b6b73]">Upload and analyze an audio file first</p>
      </div>
      
      <div v-else class="space-y-5">
        <!-- Output Type Selection -->
        <div>
          <label class="block text-sm font-medium text-[#a0a0a8] mb-3">Output Type</label>
          <div class="flex flex-wrap gap-2">
            <button
              v-for="type in outputTypes"
              :key="type.value"
              @click="selectedType = type.value"
              :class="[
                'px-4 py-2.5 rounded-xl border transition-all text-sm font-medium cursor-pointer',
                selectedType === type.value
                  ? 'border-[#d4a55a] bg-[#d4a55a]/10 text-[#d4a55a]'
                  : 'border-[#3a3a42] hover:border-[#4a4a52] text-[#a0a0a8] hover:text-[#f5f5f5]'
              ]"
            >
              {{ type.label }}
            </button>
          </div>
        </div>
        
        <!-- Rhythm Correction Strength -->
        <div>
          <div class="flex items-center justify-between mb-2">
            <label class="block text-sm font-medium text-[#a0a0a8]">Rhythm Correction</label>
            <span class="text-sm text-[#d4a55a] font-medium">
              {{ store.correctionStrength === 0 ? 'Off' : Math.round(store.correctionStrength * 100) + '%' }}
            </span>
          </div>
          <input 
            type="range" 
            v-model.number="store.correctionStrength" 
            min="0" 
            max="1" 
            step="0.1"
            class="w-full h-2 bg-[#333338] rounded-lg appearance-none cursor-pointer accent-[#d4a55a]"
          />
          <div class="flex justify-between text-xs text-[#6b6b73] mt-1">
            <span>Off</span>
            <span>Light</span>
            <span>Medium</span>
            <span>Strong</span>
            <span>Max</span>
          </div>
        </div>
        
        <!-- Generate Button -->
        <div class="flex flex-wrap gap-3 pt-2">
          <button 
            @click="store.generateSheetMusic(selectedType)"
            :disabled="store.isLoading || !store.hasFile"
            class="px-6 py-3 bg-[#d4a55a] text-[#1a1a1f] rounded-xl font-semibold hover:bg-[#e5b86b] transition-colors flex items-center gap-2 cursor-pointer disabled:opacity-50 shadow-lg shadow-[#d4a55a]/10"
          >
            <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
            Generate Sheet Music
          </button>
        </div>
      </div>
    </div>
    
    <!-- Sheet Music Display -->
    <div v-if="store.sheet?.content" class="bg-[#2a2a30]/80 backdrop-blur-sm rounded-xl border border-[#3a3a42] p-6">
      <div class="flex items-center justify-between mb-4">
        <h3 class="font-semibold text-[#f5f5f5]">Generated Sheet Music</h3>
        <div class="flex gap-2">
          <button @click="store.downloadMusicXML()" class="px-4 py-2 bg-[#333338] text-[#a0a0a8] rounded-lg font-medium text-sm hover:bg-[#3a3a42] hover:text-[#f5f5f5] transition-colors cursor-pointer border border-[#3a3a42]">
            Download MusicXML
          </button>
          <button 
            v-if="store.midiBase64" 
            @click="store.downloadMidi()" 
            class="px-4 py-2 bg-[#333338] text-[#a0a0a8] rounded-lg font-medium text-sm hover:bg-[#3a3a42] hover:text-[#f5f5f5] transition-colors cursor-pointer border border-[#3a3a42]"
          >
            Download MIDI
          </button>
        </div>
      </div>
      
      <div v-if="loadError" class="p-4 bg-red-900/20 border border-red-800/30 rounded-lg text-red-400 mb-4">
        {{ loadError }}
      </div>
      
      <div v-if="isRendering" class="p-4 bg-[#d4a55a]/10 border border-[#d4a55a]/20 rounded-lg text-[#d4a55a] mb-4">
        Rendering sheet music...
      </div>
      
      <div v-if="debugInfo" class="p-4 bg-[#333338]/50 border border-[#3a3a42] rounded-lg text-[#6b6b73] mb-4 text-xs font-mono">
        <p><strong>Debug:</strong> {{ debugInfo }}</p>
      </div>
      
      <div 
        ref="sheetContainer" 
        class="bg-white rounded-lg p-4 min-h-[400px]"
      ></div>
    </div>
    
    <!-- Melody Suggestion -->
    <div v-if="store.melody" class="bg-[#2a2a30]/80 backdrop-blur-sm rounded-xl border border-[#3a3a42] p-6">
      <div class="flex items-center justify-between mb-4">
        <h3 class="font-semibold text-[#f5f5f5]">Suggested Melody</h3>
        <button @click="store.downloadMidi()" class="px-4 py-2 bg-[#333338] text-[#a0a0a8] rounded-lg font-medium text-sm hover:bg-[#3a3a42] hover:text-[#f5f5f5] transition-colors cursor-pointer border border-[#3a3a42]">
          Download MIDI
        </button>
      </div>
      
      <div class="p-4 bg-[#d4a55a]/10 rounded-lg border border-[#d4a55a]/20">
        <p class="text-sm text-[#d4a55a] mb-2">
          Generated {{ store.melody?.notes?.length || 0 }} notes
        </p>
        <p class="text-xs text-[#a8844a]">
          Download the MIDI file to hear the suggested melody
        </p>
      </div>
    </div>
  </div>
</template>
