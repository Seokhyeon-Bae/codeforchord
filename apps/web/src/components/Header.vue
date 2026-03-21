<script setup>
</script>

<template>
  <header class="bg-white border-b border-gray-200 sticky top-0 z-40">
    <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
      <div class="flex items-center justify-between h-16">
        <!-- Logo -->
        <div class="flex items-center">
          <div class="w-10 h-10 bg-gradient-to-br from-sky-500 to-fuchsia-500 rounded-xl flex items-center justify-center">
            <svg class="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 19V6l12-3v13M9 19c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zm12-3c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zM9 10l12-3" />
            </svg>
          </div>
          <div class="ml-3">
            <h1 class="text-xl font-bold text-gray-900">CodeForChord</h1>
            <p class="text-xs text-gray-500">AI Music Transcription</p>
          </div>
        </div>
        
        <!-- Nav Links -->
        <nav class="hidden md:flex items-center space-x-6">
          <a href="#" class="text-gray-600 hover:text-gray-900 text-sm font-medium">How it works</a>
          <a href="#" class="text-gray-600 hover:text-gray-900 text-sm font-medium">Pricing</a>
          <a href="#" class="text-gray-600 hover:text-gray-900 text-sm font-medium">API</a>
        </nav>
        
        <!-- Actions -->
        <div class="flex items-center space-x-3">
          <button class="px-4 py-2 bg-gray-200 text-gray-800 rounded-lg font-medium text-sm hover:bg-gray-300 transition-colors hidden sm:inline-flex cursor-pointer">
            Sign In
          </button>
          <button class="px-4 py-2 bg-sky-600 text-white rounded-lg font-medium text-sm hover:bg-sky-700 transition-colors cursor-pointer">
            Get Started
          </button>
        </div>
      </div>
    </div>
  </header>
</template>
