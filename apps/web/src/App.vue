<script setup>
import { ref, watch, onMounted } from 'vue'
import { useAuth0 } from '@auth0/auth0-vue'
import { setTokenGetter } from './api/client'
import Header from './components/Header.vue'
import FileUpload from './components/FileUpload.vue'
import Recorder from './components/Recorder.vue'
import AnalysisPanel from './components/AnalysisPanel.vue'
import SheetViewer from './components/SheetViewer.vue'
import ArrangementTools from './components/ArrangementTools.vue'
import ChordDisplay from './components/ChordDisplay.vue'
import { useAudioStore } from './stores/audio'

const { getAccessTokenSilently } = useAuth0()
const store = useAudioStore()
const activeTab = ref('upload')

const tabs = [
  { id: 'upload', label: 'Upload', icon: 'M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12' },
  { id: 'record', label: 'Record', icon: 'M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z' },
  { id: 'analysis', label: 'Analysis', icon: 'M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z' },
  { id: 'sheet', label: 'Sheet', icon: 'M9 19V6l12-3v13M9 19c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zm12-3c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zM9 10l12-3' },
  { id: 'arrange', label: 'Arrange', icon: 'M12 6V4m0 2a2 2 0 100 4m0-4a2 2 0 110 4m-6 8a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4m6 6v10m6-2a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4' },
]

onMounted(() => {
  setTokenGetter(getAccessTokenSilently)
})

watch(() => store.sheet, (newSheet) => {
  if (newSheet?.content) {
    activeTab.value = 'sheet'
  }
})
</script>

<template>
  <div class="min-h-screen bg-[#1a1a1f] relative overflow-hidden">
    <!-- Background Image with Overlay -->
    <div class="fixed inset-0 z-0">
      <img 
        src="/image/notes.png" 
        alt="" 
        class="w-full h-full object-cover opacity-15"
      />
      <div class="absolute inset-0 bg-gradient-to-b from-[#1a1a1f]/80 via-[#1a1a1f]/95 to-[#1a1a1f]"></div>
    </div>
    
    <!-- Content -->
    <div class="relative z-10">
      <Header />
      
      <main class="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <!-- Navigation Tabs -->
        <div class="flex space-x-1 bg-[#242429]/80 backdrop-blur-sm rounded-xl p-1.5 mb-8 border border-[#3a3a42]">
          <button
            v-for="tab in tabs"
            :key="tab.id"
            @click="activeTab = tab.id"
            :class="[
              'flex-1 py-2.5 px-4 rounded-lg font-medium text-sm transition-all cursor-pointer flex items-center justify-center gap-2',
              activeTab === tab.id
                ? 'bg-[#d4a55a] text-[#1a1a1f] shadow-lg'
                : 'text-[#a0a0a8] hover:text-[#f5f5f5] hover:bg-[#333338]'
            ]"
          >
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" :d="tab.icon" />
            </svg>
            <span class="hidden sm:inline">{{ tab.label }}</span>
          </button>
        </div>
        
        <!-- Error Display -->
        <div 
          v-if="store.error" 
          class="mb-6 p-4 bg-red-900/30 border border-red-800/50 rounded-xl text-red-300 backdrop-blur-sm"
        >
          <div class="flex items-center">
            <svg class="w-5 h-5 mr-2" fill="currentColor" viewBox="0 0 20 20">
              <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clip-rule="evenodd" />
            </svg>
            {{ store.error }}
          </div>
        </div>
        
        <!-- Loading Overlay -->
        <div 
          v-if="store.isLoading" 
          class="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50"
        >
          <div class="bg-[#2a2a30] rounded-2xl p-8 shadow-2xl flex flex-col items-center border border-[#3a3a42]">
            <div class="animate-spin h-12 w-12 border-4 border-[#d4a55a] border-t-transparent rounded-full mb-4"></div>
            <p class="text-[#f5f5f5] font-medium">Processing audio...</p>
            <p class="text-[#6b6b73] text-sm mt-1">This may take a moment</p>
          </div>
        </div>
        
        <!-- Tab Content -->
        <div class="space-y-6 fade-in">
          <!-- Upload Tab -->
          <div v-show="activeTab === 'upload'">
            <FileUpload @file-selected="(f) => { store.setFile(f); activeTab = 'analysis' }" />
          </div>

          <!-- Record Tab -->
          <div v-show="activeTab === 'record'">
            <Recorder @file-selected="(f) => { store.setFile(f, 'recording'); activeTab = 'analysis' }" />
            
            <div v-if="store.hasFile" class="mt-6 bg-[#2a2a30]/80 backdrop-blur-sm rounded-xl border border-[#3a3a42] p-6">
              <h3 class="font-semibold text-[#f5f5f5] mb-4">Selected File</h3>
              <div class="flex items-center justify-between">
                <div class="flex items-center">
                  <div class="w-10 h-10 bg-[#d4a55a]/20 rounded-lg flex items-center justify-center mr-3">
                    <svg class="w-5 h-5 text-[#d4a55a]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 19V6l12-3v13M9 19c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zm12-3c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zM9 10l12-3" />
                    </svg>
                  </div>
                  <div>
                    <p class="font-medium text-[#f5f5f5]">{{ store.fileName }}</p>
                    <p class="text-sm text-[#6b6b73]">Ready for analysis</p>
                  </div>
                </div>
                <button @click="store.reset()" class="px-4 py-2 bg-[#333338] text-[#a0a0a8] rounded-lg font-medium hover:bg-[#3a3a42] hover:text-[#f5f5f5] transition-colors cursor-pointer">
                  Remove
                </button>
              </div>
            </div>
          </div>
          
          <!-- Analysis Tab -->
          <div v-show="activeTab === 'analysis'">
            <AnalysisPanel />
            <ChordDisplay v-if="store.chords" class="mt-6" />
          </div>
          
          <!-- Sheet Tab -->
          <div v-show="activeTab === 'sheet'">
            <SheetViewer />
          </div>
          
          <!-- Arrange Tab -->
          <div v-show="activeTab === 'arrange'">
            <ArrangementTools />
          </div>
        </div>
      </main>
      
      <!-- Footer -->
      <footer class="mt-16 py-8 border-t border-[#3a3a42]">
        <div class="max-w-6xl mx-auto px-4 text-center">
          <p class="text-[#6b6b73] text-sm">CodeForChord - AI-Powered Music Transcription</p>
        </div>
      </footer>
    </div>
  </div>
</template>
