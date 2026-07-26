<template>
  <div class="h-screen w-screen flex bg-nms-bg text-slate-100 overflow-hidden">
    <!-- Left Scrollable Sidebar with Pinned Bottom Settings Bar -->
    <ScrollableSidebar />

    <!-- Main Workspace Container -->
    <div class="flex-1 flex flex-col h-screen overflow-hidden">
      <!-- Global Top Header -->
      <GlobalHeader />

      <!-- Main Canvas / Route Content Area -->
      <main class="flex-1 overflow-y-auto p-6 custom-scroll bg-gradient-to-b from-[#0b0f19] to-[#0d1322]">
        <router-view v-slot="{ Component }">
          <transition name="fade" mode="out-in">
            <component :is="Component" />
          </transition>
        </router-view>
      </main>
    </div>
  </div>
</template>

<script setup lang="ts">
import ScrollableSidebar from './ScrollableSidebar.vue'
import GlobalHeader from './GlobalHeader.vue'
</script>

<style scoped>
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.15s ease;
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
