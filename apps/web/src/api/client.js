import axios from 'axios'

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 120000, // 2 minutes for audio processing
})

// Request interceptor
api.interceptors.request.use(
  (config) => {
    // Add auth token if available
    const token = localStorage.getItem('token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => Promise.reject(error)
)

// Response interceptor
api.interceptors.response.use(
  (response) => response,
  (error) => {
    console.error('API Error:', error.response?.data || error.message)
    return Promise.reject(error)
  }
)

export default api

// Detection endpoints
export const detectNotes = async (file, options = {}) => {
  const formData = new FormData()
  formData.append('file', file)
  
  const params = new URLSearchParams()
  if (options.onsetThreshold) params.append('onset_threshold', options.onsetThreshold)
  if (options.frameThreshold) params.append('frame_threshold', options.frameThreshold)
  if (options.minConfidence) params.append('min_confidence', options.minConfidence)
  
  const response = await api.post(`/detect/notes?${params}`, formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
  return response.data
}

export const detectChords = async (file) => {
  const formData = new FormData()
  formData.append('file', file)
  
  const response = await api.post('/detect/chords', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
  return response.data
}

export const detectFull = async (file, instrument = 'piano') => {
  const formData = new FormData()
  formData.append('file', file)
  
  const response = await api.post(`/detect/full?instrument=${instrument}`, formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
  return response.data
}

// Generation endpoints
export const generateSheet = async (file, options = {}) => {
  const formData = new FormData()
  formData.append('file', file)
  
  const params = new URLSearchParams()
  params.append('output_format', options.format || 'musicxml')
  params.append('output_type', options.type || 'lead_sheet')
  params.append('title', options.title || 'Untitled')
  params.append('tempo', options.tempo || 120)
  params.append('time_signature', options.timeSignature || '4/4')
  params.append('instrument', options.instrument || 'piano')
  params.append('correction_strength', options.correctionStrength ?? 0.5)
  
  const response = await api.post(`/generate/sheet?${params}`, formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
  return response.data
}

export const generateMelody = async (file, options = {}) => {
  const formData = new FormData()
  formData.append('file', file)
  
  const params = new URLSearchParams()
  params.append('style', options.style || 'simple')
  params.append('octave', options.octave || 4)
  params.append('tempo', options.tempo || 120)
  
  const response = await api.post(`/generate/melody?${params}`, formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
  return response.data
}

export const generateMelodyFromChords = async (chords, options = {}) => {
  const params = new URLSearchParams()
  params.append('style', options.style || 'simple')
  params.append('octave', options.octave || 4)
  params.append('tempo', options.tempo || 120)
  
  const response = await api.post(`/generate/melody/from-chords?${params}`, chords)
  return response.data
}

// Arrangement endpoints
export const transpose = async (file, semitones, options = {}) => {
  const formData = new FormData()
  formData.append('file', file)
  
  const params = new URLSearchParams()
  params.append('semitones', semitones)
  params.append('output_format', options.format || 'musicxml')
  params.append('tempo', options.tempo || 120)
  
  const response = await api.post(`/arrange/transpose?${params}`, formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
  return response.data
}

export const convertMode = async (file, targetMode, options = {}) => {
  const formData = new FormData()
  formData.append('file', file)
  
  const params = new URLSearchParams()
  params.append('target_mode', targetMode)
  params.append('output_format', options.format || 'musicxml')
  
  const response = await api.post(`/arrange/convert-mode?${params}`, formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
  return response.data
}

export const simplifyChords = async (file, targetInstrument = 'guitar') => {
  const formData = new FormData()
  formData.append('file', file)
  
  const response = await api.post(`/arrange/simplify?target_instrument=${targetInstrument}`, formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
  return response.data
}

export const jazzifyChords = async (file) => {
  const formData = new FormData()
  formData.append('file', file)
  
  const response = await api.post('/arrange/jazzify', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
  return response.data
}

// Health check
export const healthCheck = async () => {
  const response = await api.get('/health')
  return response.data
}
