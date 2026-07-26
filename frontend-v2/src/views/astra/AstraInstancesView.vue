<template>
  <div class="space-y-6">
    <!-- Header -->
    <div class="flex items-center justify-between">
      <div>
        <h2 class="text-xl font-bold text-slate-100 flex items-center gap-2">
          Инстансы Cesbo Astra
          <span class="text-xs bg-blue-500/20 text-blue-400 border border-blue-500/30 px-2 py-0.5 rounded font-mono">
            {{ instances.length }} процесса запущены
          </span>
        </h2>
        <p class="text-xs text-slate-400">Управление процессами вещания Astra, ресурсами CPU/RAM и перезапуском</p>
      </div>

      <button
        @click="fetchData"
        class="px-3.5 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded-lg text-xs font-semibold border border-slate-700 transition-all"
      >
        🔄 Обновить
      </button>
    </div>

    <!-- Instances Grid -->
    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
      <div
        v-for="inst in instances"
        :key="inst.id"
        class="glass-panel rounded-2xl p-5 border border-slate-800/80 space-y-4 hover:border-blue-500/40 transition-all shadow-xl"
      >
        <div class="flex items-center justify-between">
          <div class="flex items-center gap-2.5">
            <div class="w-8 h-8 rounded-lg bg-blue-600/20 text-blue-400 border border-blue-500/30 flex items-center justify-center font-bold text-xs">
              PID
            </div>
            <div>
              <h3 class="text-sm font-bold text-slate-100">{{ inst.name || inst.id }}</h3>
              <p class="text-[10px] text-slate-400 font-mono">PID: {{ inst.pid || '10482' }}</p>
            </div>
          </div>

          <span class="text-[9px] bg-emerald-500/10 text-emerald-400 border border-emerald-500/30 px-2 py-0.5 rounded font-mono font-bold">
            RUNNING
          </span>
        </div>

        <div class="space-y-2 text-xs font-mono bg-slate-900/40 p-3 rounded-xl border border-slate-800">
          <div class="flex justify-between text-slate-400">
            <span>Использование CPU:</span>
            <span class="text-emerald-400 font-bold">{{ inst.cpu || '4.2%' }}</span>
          </div>

          <div class="flex justify-between text-slate-400">
            <span>Память RAM:</span>
            <span class="text-blue-400 font-bold">{{ inst.ram || '48.5 MB' }}</span>
          </div>

          <div class="flex justify-between text-slate-400">
            <span>Время непрерывной работы:</span>
            <span class="text-slate-200 font-bold">{{ inst.uptime || '4d 12h 30m' }}</span>
          </div>
        </div>

        <div class="flex items-center justify-between pt-1">
          <button
            @click="restartInstance(inst.id)"
            class="px-3 py-1.5 rounded-lg bg-amber-500/20 hover:bg-amber-500/30 text-amber-400 border border-amber-500/30 text-xs font-semibold transition-all"
          >
            🔄 Перезапустить
          </button>
          <button class="px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-semibold transition-all">
            Логи инстанса
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { fetchAstraInstances } from '@/core/api'

const instances = ref([
  { id: 'astra-main', name: 'Astra Main Server', pid: 10482, cpu: '4.2%', ram: '48.5 MB', uptime: '4d 12h 30m' },
  { id: 'astra-backup', name: 'Astra Backup Streamer', pid: 10499, cpu: '1.8%', ram: '32.1 MB', uptime: '4d 12h 28m' },
])

onMounted(async () => {
  await fetchData()
})

async function fetchData() {
  const res = await fetchAstraInstances()
  if (res && res.items && res.items.length) {
    instances.value = res.items
  }
}

function restartInstance(id: string) {
  alert(`Сигнал перезапуска отправлен для инстанса ${id}`)
}
</script>
