import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import * as api from '../api/client'
import { uploadAudio, uploadRecording, generateAndSaveSheet } from '../api/client'

export const useAudioStore = defineStore('audio', () => {
  // State
  const file = ref(null)
  const fileName = ref('')
  const isLoading = ref(false)
  const error = ref(null)
  
  // Analysis results
  const notes = ref(null)
  const chords = ref(null)
  const detectedKey = ref(null)
  const tempoInfo = ref(null)
  const timeSignatureInfo = ref(null)
  
  // Cloud storage
  const blobName = ref(null)
  const isUploading = ref(false)
  const sheetId = ref(null)

  // Generated content
  const sheet = ref(null)
  const melody = ref(null)
  const midiBase64 = ref(null)
  
  // Settings
  const instrument = ref('piano')
  const tempo = ref(120)
  const timeSignature = ref('4/4')
  const title = ref('Untitled')
  const correctionStrength = ref(0.5)  // 0-1, rhythm correction strength
  
  // Computed
  const hasFile = computed(() => file.value !== null)
  const hasAnalysis = computed(() => notes.value !== null || chords.value !== null)
  const hasSheet = computed(() => sheet.value !== null)
  
  const chordSymbols = computed(() => {
    if (!chords.value?.chords) return []
    return chords.value.chords.map(c => ({
      symbol: c.symbol,
      timestamp: c.timestamp,
      duration: c.duration,
    }))
  })
  
  // Actions
  const setFile = (newFile, uploadType = 'upload') => {
    file.value = newFile
    fileName.value = newFile?.name || ''
    blobName.value = null
    sheetId.value = null
    notes.value = null
    chords.value = null
    sheet.value = null
    melody.value = null
    error.value = null

    // Upload to Azure in background
    uploadToCloud(newFile, uploadType)
  }

  const uploadToCloud = async (newFile, uploadType = 'upload') => {
    if (!newFile) return
    isUploading.value = true
    try {
      const fn = uploadType === 'recording' ? uploadRecording : uploadAudio
      const result = await fn(newFile)
      blobName.value = result.blob_name
    } catch (e) {
      // Cloud upload failure is non-fatal — stateless fallback still works
      console.warn('Cloud upload failed, falling back to stateless mode:', e.message)
    } finally {
      isUploading.value = false
    }
  }
  
  const analyzeAudio = async () => {
    if (!file.value) {
      error.value = 'No file selected'
      return
    }
    
    isLoading.value = true
    error.value = null
    
    try {
      const result = await api.detectFull(file.value, instrument.value)
      notes.value = result.notes
      chords.value = result.chords
      detectedKey.value = result.chords?.key
      
      // Auto-set tempo and time signature from detection
      if (result.tempo_info) {
        tempoInfo.value = result.tempo_info
        tempo.value = result.tempo_info.tempo || 120
      }
      if (result.time_signature_info) {
        timeSignatureInfo.value = result.time_signature_info
        timeSignature.value = result.time_signature_info.time_signature || '4/4'
      }
    } catch (e) {
      error.value = e.response?.data?.detail || e.message
    } finally {
      isLoading.value = false
    }
  }
  
  const detectChordsOnly = async () => {
    if (!file.value) return
    
    isLoading.value = true
    error.value = null
    
    try {
      chords.value = await api.detectChords(file.value)
      detectedKey.value = chords.value.key
    } catch (e) {
      error.value = e.response?.data?.detail || e.message
    } finally {
      isLoading.value = false
    }
  }
  
  const generateSheetMusic = async (outputType = 'lead_sheet') => {
    if (!file.value) return

    isLoading.value = true
    error.value = null

    try {
      if (blobName.value) {
        // Cloud path: generate from Azure blob → save to MongoDB
        const result = await generateAndSaveSheet(blobName.value, {
          format: 'musicxml',
          type: outputType,
          title: title.value,
          tempo: tempo.value,
          timeSignature: timeSignature.value,
          instrument: instrument.value,
          correctionStrength: correctionStrength.value,
        })
        sheetId.value = result.sheet_id
        sheet.value = result
      } else {
        // Stateless fallback (Azure upload not yet done)
        const result = await api.generateSheet(file.value, {
          format: 'musicxml',
          type: outputType,
          title: title.value,
          tempo: tempo.value,
          timeSignature: timeSignature.value,
          instrument: instrument.value,
          correctionStrength: correctionStrength.value,
        })
        sheet.value = result
      }
    } catch (e) {
      error.value = e.response?.data?.detail || e.message
    } finally {
      isLoading.value = false
    }
  }
  
  const generateMelodySuggestion = async (style = 'simple') => {
    if (!file.value) return
    
    isLoading.value = true
    error.value = null
    
    try {
      const result = await api.generateMelody(file.value, {
        style,
        tempo: tempo.value,
      })
      melody.value = result.melody
      midiBase64.value = result.midi_base64
    } catch (e) {
      error.value = e.response?.data?.detail || e.message
    } finally {
      isLoading.value = false
    }
  }
  
  const transposeMusic = async (semitones) => {
    if (!file.value) return
    
    isLoading.value = true
    error.value = null
    
    try {
      const result = await api.transpose(file.value, semitones, {
        tempo: tempo.value,
      })
      sheet.value = { content: result.musicxml }
      chords.value = result.chords
    } catch (e) {
      error.value = e.response?.data?.detail || e.message
    } finally {
      isLoading.value = false
    }
  }
  
  const convertToMode = async (mode) => {
    if (!chords.value) {
      error.value = 'No chords detected. Run "Chords Only" analysis first.'
      return
    }
    
    isLoading.value = true
    error.value = null
    
    try {
      const result = await api.convertModeChords(chords.value, mode)
      chords.value = result
      // Clear sheet so user regenerates with new chords
      sheet.value = null
    } catch (e) {
      error.value = e.response?.data?.detail || e.message
    } finally {
      isLoading.value = false
    }
  }
  
  const reset = () => {
    file.value = null
    fileName.value = ''
    blobName.value = null
    sheetId.value = null
    notes.value = null
    chords.value = null
    sheet.value = null
    melody.value = null
    midiBase64.value = null
    error.value = null
    detectedKey.value = null
    tempoInfo.value = null
    timeSignatureInfo.value = null
    tempo.value = 120
    timeSignature.value = '4/4'
    correctionStrength.value = 0.5
  }
  
  const downloadMidi = () => {
    if (!midiBase64.value) return
    
    const byteCharacters = atob(midiBase64.value)
    const byteNumbers = new Array(byteCharacters.length)
    for (let i = 0; i < byteCharacters.length; i++) {
      byteNumbers[i] = byteCharacters.charCodeAt(i)
    }
    const byteArray = new Uint8Array(byteNumbers)
    const blob = new Blob([byteArray], { type: 'audio/midi' })
    
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `${title.value || 'melody'}.mid`
    a.click()
    URL.revokeObjectURL(url)
  }
  
  const downloadMusicXML = () => {
    if (!sheet.value?.content) return
    
    const blob = new Blob([sheet.value.content], { type: 'application/vnd.recordare.musicxml+xml' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `${title.value || 'sheet'}.musicxml`
    a.click()
    URL.revokeObjectURL(url)
  }
  
  const downloadAudio = () => {
    if (!file.value) return
    
    const url = URL.createObjectURL(file.value)
    const a = document.createElement('a')
    a.href = url
    a.download = file.value.name || 'recording.webm'
    a.click()
    URL.revokeObjectURL(url)
  }
  
  return {
    // State
    file,
    fileName,
    isLoading,
    isUploading,
    blobName,
    sheetId,
    error,
    notes,
    chords,
    detectedKey,
    tempoInfo,
    timeSignatureInfo,
    sheet,
    melody,
    midiBase64,
    instrument,
    tempo,
    timeSignature,
    title,
    correctionStrength,
    
    // Computed
    hasFile,
    hasAnalysis,
    hasSheet,
    chordSymbols,
    
    // Actions
    setFile,
    uploadToCloud,
    analyzeAudio,
    detectChordsOnly,
    generateSheetMusic,
    generateMelodySuggestion,
    transposeMusic,
    convertToMode,
    reset,
    downloadMidi,
    downloadMusicXML,
    downloadAudio,
  }
})
