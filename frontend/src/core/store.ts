/**
 * Pinia store — глобальное состояние приложения.
 */
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { ModuleManifest, SidebarGroup, MenuItem } from '@/modules/types'
import { fetchModules, fetchLoadedModules, fetchRoot } from '@/core/api'

export const useAppStore = defineStore('app', () => {
    // ── State ──────────────────────────────────────────────────────
    const backendOk = ref(true)
    const modules = ref<ModuleManifest[]>([])
    const loadedModuleIds = ref<string[]>([])
    const groupOpen = ref<Record<string, boolean>>({})
    const loading = ref(false)
    const lastSettingsUpdate = ref(Date.now())

    // ── Getters ────────────────────────────────────────────────────
    const sidebarGroups = computed<SidebarGroup[]>(() => {
        return modules.value
            .filter(
                (mod) =>
                    mod.menu &&
                    mod.menu.location === 'sidebar' &&
                    !mod.is_submodule,
            )
            .map((mod) => ({
                id: mod.id,
                label: mod.menu!.group || mod.name,
                items: mod.menu!.items || [],
            }))
    })

    const footerItems = computed<MenuItem[]>(() => {
        return modules.value
            .filter((mod) => mod.menu && mod.menu.location === 'footer')
            .flatMap((mod) => mod.menu!.items || [])
    })

    // ── Actions ────────────────────────────────────────────────────
    async function checkBackend() {
        try {
            await fetchRoot()
            backendOk.value = true
        } catch {
            backendOk.value = false
        }
    }

    async function loadModules() {
        loading.value = true
        try {
            const [modulesRes, loadedRes] = await Promise.all([
                fetchModules(false, true),
                fetchLoadedModules(),
            ])
            modules.value = modulesRes.items || []
            loadedModuleIds.value = loadedRes.items || []

            // Initialize group open state
            const openState: Record<string, boolean> = {}
            for (const group of sidebarGroups.value) {
                openState[group.id] = groupOpen.value[group.id] ?? true
            }
            groupOpen.value = openState
        } catch {
            // fallback: empty
            modules.value = []
            loadedModuleIds.value = []
        } finally {
            loading.value = false
        }
    }

    function toggleGroup(id: string) {
        groupOpen.value = {
            ...groupOpen.value,
            [id]: !groupOpen.value[id],
        }
    }

    function triggerSettingsUpdate() {
        lastSettingsUpdate.value = Date.now()
    }

    return {
        // State
        backendOk,
        modules,
        loadedModuleIds,
        groupOpen,
        loading,
        lastSettingsUpdate,
        // Getters
        sidebarGroups,
        footerItems,
        // Actions
        checkBackend,
        loadModules,
        toggleGroup,
        triggerSettingsUpdate,
    }
})
