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

onMounted(() => {
  setTokenGetter(getAccessTokenSilently)
})

// Auto-switch to sheet tab when sheet is generated
watch(() => store.sheet, (newSheet) => {
  if (newSheet?.content) {
    activeTab.value = 'sheet'
  }
})
</script>

<template>
  <div class="min-h-screen bg-gradient-to-br from-gray-50 to-gray-100">
    <Header />
    
    <main class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <!-- Navigation Tabs -->
      <div class="flex space-x-1 bg-white rounded-xl p-1 shadow-sm mb-8">
        <button
          v-for="tab in ['upload', 'record', 'analysis', 'sheet', 'arrange']"
          :key="tab"
          @click="activeTab = tab"
          :class="[
            'flex-1 py-2.5 px-4 rounded-lg font-medium text-sm transition-all cursor-pointer',
            activeTab === tab
              ? 'bg-sky-600 text-white shadow-sm'
              : 'text-gray-600 hover:text-gray-900 hover:bg-gray-100'
          ]"
        >
          {{ tab === 'record' ? '녹음' : tab.charAt(0).toUpperCase() + tab.slice(1) }}
        </button>
      </div>
      
      <!-- Error Display -->
      <div 
        v-if="store.error" 
        class="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg text-red-700"
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
        class="fixed inset-0 bg-black/30 backdrop-blur-sm flex items-center justify-center z-50"
      >
        <div class="bg-white rounded-2xl p-8 shadow-xl flex flex-col items-center">
          <div class="animate-spin h-12 w-12 border-4 border-sky-600 border-t-transparent rounded-full mb-4"></div>
          <p class="text-gray-700 font-medium">Processing audio...</p>
          <p class="text-gray-500 text-sm mt-1">This may take a moment</p>
        </div>
      </div>
      
      <!-- Tab Content -->
      <div class="space-y-6">
        <!-- Upload Tab -->
        <div v-show="activeTab === 'upload'">
          <FileUpload @file-selected="(f) => { store.setFile(f); activeTab = 'analysis' }" />

        <!-- Record Tab -->
        </div>
        <div v-show="activeTab === 'record'">
          <Recorder @file-selected="(f) => { store.setFile(f, 'recording'); activeTab = 'analysis' }" />
          
          <div v-if="store.hasFile" class="mt-6 bg-white rounded-xl shadow-sm border border-gray-200 p-6">
            <h3 class="font-semibold text-gray-900 mb-4">Selected File</h3>
            <div class="flex items-center justify-between">
              <div class="flex items-center">
                <div class="w-10 h-10 bg-sky-100 rounded-lg flex items-center justify-center mr-3">
                  <svg class="w-5 h-5 text-sky-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 19V6l12-3v13M9 19c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zm12-3c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zM9 10l12-3" />
                  </svg>
                </div>
                <div>
                  <p class="font-medium text-gray-900">{{ store.fileName }}</p>
                  <p class="text-sm text-gray-500">Ready for analysis</p>
                </div>
              </div>
              <button @click="store.reset()" class="px-4 py-2 bg-gray-200 text-gray-800 rounded-lg font-medium hover:bg-gray-300 transition-colors cursor-pointer">
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
    <footer class="mt-16 py-8 border-t border-gray-200 bg-white">
      <div class="max-w-7xl mx-auto px-4 text-center text-gray-500 text-sm">
        <p>CodeForChord - AI-Powered Music Transcription</p>
      </div>
    </footer>
  </div>
</template>
