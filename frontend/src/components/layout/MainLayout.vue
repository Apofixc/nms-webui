<template>
  <div v-if="$route.path === '/login'" class="h-screen w-full overflow-hidden bg-background">
    <router-view />
  </div>

  <div v-else class="h-screen min-h-0 w-full flex flex-shrink-0 overflow-hidden bg-background text-on-surface">
    <Sidebar />
    <main class="flex-1 min-h-0 min-w-0 flex flex-col overflow-hidden">
      <Header />

      <!-- Fixed Secondary Horizontal Navigation Bar for Settings Routes (Matching Stitch mockups) -->
      <nav
        v-if="$route.path.startsWith('/settings')"
        class="bg-surface-container-low border-b border-outline-variant px-6 flex items-center gap-6 text-sm font-medium flex-shrink-0 z-30"
      >
        <router-link
          to="/settings"
          class="py-3.5 px-1 border-b-2 transition-all border-transparent text-on-surface-variant hover:text-on-surface"
          :class="($route.path === '/settings' || $route.path === '/settings/modules') && '!border-primary !text-primary font-bold'"
        >
          Configuration
        </router-link>

        <router-link
          to="/settings/profile"
          class="py-3.5 px-1 border-b-2 transition-all border-transparent text-on-surface-variant hover:text-on-surface"
          active-class="!border-primary !text-primary font-bold"
        >
          User Profile
        </router-link>

        <router-link
          to="/settings/users"
          class="py-3.5 px-1 border-b-2 transition-all border-transparent text-on-surface-variant hover:text-on-surface"
          active-class="!border-primary !text-primary font-bold"
        >
          Users Management
        </router-link>

        <router-link
          to="/settings/access-control"
          class="py-3.5 px-1 border-b-2 transition-all border-transparent text-on-surface-variant hover:text-on-surface"
          active-class="!border-primary !text-primary font-bold"
        >
          Access Control
        </router-link>
      </nav>

      <!-- Main Content Area -->
      <div class="flex-1 min-h-0 min-w-0 overflow-y-auto overflow-x-hidden bg-background">
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
