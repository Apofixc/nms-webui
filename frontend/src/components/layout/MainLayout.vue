<template>
  <div class="h-screen min-h-0 min-w-[768px] w-full flex flex-shrink-0 overflow-hidden">
    <Sidebar />
    <main class="flex-1 min-h-0 min-w-[400px] flex flex-col overflow-hidden">
      <Header />
      <div class="flex-1 min-h-0 min-w-0 overflow-y-auto overflow-x-hidden">
        <router-view v-slot="{ Component }">
          <transition name="page" mode="out-in">
            <component :is="Component" v-if="Component" />
          </transition>
        </router-view>
      </div>
    </main>
  </div>
</template>

<script setup lang="ts">
import Sidebar from './Sidebar.vue'
import Header from './Header.vue'
</script>

<style scoped>
.page-enter-active,
.page-leave-active { transition: opacity 0.12s ease, transform 0.12s ease; }
.page-enter-from { opacity: 0; transform: translateY(4px); }
.page-leave-to { opacity: 0; transform: translateY(-2px); }
</style>
