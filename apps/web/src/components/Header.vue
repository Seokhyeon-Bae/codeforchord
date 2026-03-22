<script setup>
import { ref } from 'vue'
import { useAuth0 } from '@auth0/auth0-vue'
import { getAppOrigin } from '@/config/appOrigin'
import MarketingNavModal from './MarketingNavModal.vue'

const { isAuthenticated, isLoading, user, loginWithRedirect, logout } = useAuth0()

const navSection = ref(null) // 'how' | 'pricing' | 'api' | null

function openNav(section) {
  navSection.value = section
}
function closeNav() {
  navSection.value = null
}

const login = async () => {
  try {
    await loginWithRedirect()
  } catch (e) {
    console.error('login error:', e)
  }
}
const handleLogout = () => logout({ logoutParams: { returnTo: getAppOrigin() } })
</script>

<template>
  <header class="bg-[#242429]/90 backdrop-blur-md border-b border-[#3a3a42] sticky top-0 z-40">
    <div class="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8">
      <div class="grid grid-cols-[minmax(0,auto)_1fr_minmax(0,auto)] items-center gap-3 h-16">
        <!-- Logo -->
        <div class="flex items-center min-w-0">
          <img
            src="/favicon.png"
            alt="CodeForChord"
            width="40"
            height="40"
            class="w-10 h-10 rounded-xl object-contain bg-[#1a1a1f] shadow-lg ring-1 ring-[#3a3a42]/60 shrink-0"
          />
          <div class="ml-3">
            <h1 class="text-xl font-bold text-[#f5f5f5] tracking-tight">CodeForChord</h1>
            <p class="text-xs text-[#6b6b73]">AI Music Transcription</p>
          </div>
        </div>

        <!-- Nav Links -->
        <nav class="flex flex-wrap items-center justify-center gap-x-4 sm:gap-x-6 md:gap-x-8 min-w-0">
          <button
            type="button"
            class="text-[#a0a0a8] hover:text-[#d4a55a] text-sm font-medium transition-colors cursor-pointer bg-transparent border-0 p-0"
            @click="openNav('how')"
          >
            How it works
          </button>
          <button
            type="button"
            class="text-[#a0a0a8] hover:text-[#d4a55a] text-sm font-medium transition-colors cursor-pointer bg-transparent border-0 p-0"
            @click="openNav('pricing')"
          >
            Pricing
          </button>
          <button
            type="button"
            class="text-[#a0a0a8] hover:text-[#d4a55a] text-sm font-medium transition-colors cursor-pointer bg-transparent border-0 p-0"
            @click="openNav('api')"
          >
            API
          </button>
        </nav>

        <!-- Auth Actions -->
        <div class="flex items-center justify-end space-x-2 sm:space-x-3 shrink-0">
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
              @click="login"
              class="px-4 py-2 bg-[#d4a55a] text-[#1a1a1f] rounded-lg font-semibold text-sm hover:bg-[#e5b86b] transition-colors cursor-pointer"
            >
              Get Started
            </button>
          </template>
        </div>
      </div>
    </div>

    <MarketingNavModal :open="!!navSection" :section="navSection" @close="closeNav" />
  </header>
</template>
