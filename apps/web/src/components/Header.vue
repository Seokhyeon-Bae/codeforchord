<script setup>
import { useAuth0 } from '@auth0/auth0-vue'

const { isAuthenticated, isLoading, user, loginWithRedirect, logout } = useAuth0()

const login = async () => {
  try {
    await loginWithRedirect()
  } catch(e) {
    console.error('login error:', e)
  }
}
const signup = () => loginWithRedirect({ authorizationParams: { screen_hint: 'signup' } }).catch(e => console.error('signup error:', e))
const handleLogout = () => logout({ logoutParams: { returnTo: window.location.origin } })
</script>

<template>
  <header class="bg-[#242429]/90 backdrop-blur-md border-b border-[#3a3a42] sticky top-0 z-40">
    <div class="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8">
      <div class="flex items-center justify-between h-16">
        <!-- Logo -->
        <div class="flex items-center">
          <div class="w-10 h-10 bg-gradient-to-br from-[#d4a55a] to-[#a8844a] rounded-xl flex items-center justify-center shadow-lg">
            <svg class="w-6 h-6 text-[#1a1a1f]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 19V6l12-3v13M9 19c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zm12-3c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zM9 10l12-3" />
            </svg>
          </div>
          <div class="ml-3">
            <h1 class="text-xl font-bold text-[#f5f5f5] tracking-tight">CodeForChord</h1>
            <p class="text-xs text-[#6b6b73]">AI Music Transcription</p>
          </div>
        </div>

        <!-- Nav Links -->
        <nav class="hidden md:flex items-center space-x-8">
          <a href="#" class="text-[#a0a0a8] hover:text-[#d4a55a] text-sm font-medium transition-colors">How it works</a>
          <a href="#" class="text-[#a0a0a8] hover:text-[#d4a55a] text-sm font-medium transition-colors">Pricing</a>
          <a href="#" class="text-[#a0a0a8] hover:text-[#d4a55a] text-sm font-medium transition-colors">API</a>
        </nav>

        <!-- Auth Actions -->
        <div class="flex items-center space-x-3">
          <!-- Loading -->
          <div v-if="isLoading" class="w-8 h-8 rounded-full bg-[#333338] animate-pulse" />

          <!-- Logged in -->
          <template v-else-if="isAuthenticated">
            <div class="flex items-center space-x-3">
              <img
                v-if="user?.picture"
                :src="user.picture"
                :alt="user.name"
                class="w-8 h-8 rounded-full border-2 border-[#d4a55a]/30"
              />
              <div class="hidden sm:block">
                <p class="text-sm font-medium text-[#f5f5f5] leading-none">{{ user?.name }}</p>
                <p class="text-xs text-[#6b6b73]">{{ user?.email }}</p>
              </div>
              <button
                @click="handleLogout"
                class="px-3 py-1.5 bg-[#333338] text-[#a0a0a8] rounded-lg text-sm hover:bg-[#3a3a42] hover:text-[#f5f5f5] transition-colors cursor-pointer"
              >
                Log out
              </button>
            </div>
          </template>

          <!-- Not logged in -->
          <template v-else>
            <button
              @click="login"
              class="px-4 py-2 bg-[#333338] text-[#a0a0a8] rounded-lg font-medium text-sm hover:bg-[#3a3a42] hover:text-[#f5f5f5] transition-colors hidden sm:inline-flex cursor-pointer"
            >
              Log in
            </button>
            <button
              @click="signup"
              class="px-4 py-2 bg-[#d4a55a] text-[#1a1a1f] rounded-lg font-semibold text-sm hover:bg-[#e5b86b] transition-colors cursor-pointer"
            >
              Get Started
            </button>
          </template>
        </div>
      </div>
    </div>
  </header>
</template>
