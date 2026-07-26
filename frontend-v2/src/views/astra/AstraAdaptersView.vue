<template>
  <div class="space-y-6">
    <!-- Header Controls -->
    <div class="flex items-center justify-between">
      <div>
        <h2 class="text-xl font-bold text-slate-100 flex items-center gap-2">
          DVB Адаптеры и Тюнеры Astra
          <span class="text-xs bg-blue-500/20 text-blue-400 border border-blue-500/30 px-2 py-0.5 rounded font-mono">
            12 карт подключено
          </span>
        </h2>
        <p class="text-xs text-slate-400">Мониторинг физических тюнеров DVB-S/S2/C/T2, уровней сигнала SNR, RF-частот и захвата захват фазы (Lock)</p>
      </div>

      <button class="px-3.5 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded-lg text-xs font-semibold border border-slate-700 transition-all flex items-center gap-2">
        🔍 Сканировать транспондеры
      </button>
    </div>

    <!-- Adapters Table Card -->
    <div class="glass-panel rounded-2xl p-6 border border-slate-800/80 shadow-2xl space-y-4">
      <div class="overflow-x-auto">
        <table class="w-full text-left text-xs font-mono">
          <thead class="text-[10px] text-slate-400 uppercase bg-slate-900/80 border-b border-slate-800">
            <tr>
              <th class="py-3 px-4">ID</th>
              <th class="py-3 px-4">Модель DVB Карты</th>
              <th class="py-3 px-4">Частота / Пол.</th>
              <th class="py-3 px-4">Симв. Скорость</th>
              <th class="py-3 px-4">SNR (%)</th>
              <th class="py-3 px-4">SNR (dB)</th>
              <th class="py-3 px-4">BER Ошибки</th>
              <th class="py-3 px-4 text-right">Захват (Lock)</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-slate-800/50">
            <tr v-for="ad in adapters" :key="ad.id" class="hover:bg-slate-800/40 transition-colors">
              <td class="py-3 px-4 font-bold text-slate-200">#{{ ad.id }}</td>
              <td class="py-3 px-4 text-slate-200 font-sans flex items-center gap-2">
                <span class="w-2 h-2 rounded-full bg-emerald-400"></span>
                {{ ad.name }}
              </td>
              <td class="py-3 px-4 text-slate-300 font-bold">{{ ad.freq }}</td>
              <td class="py-3 px-4 text-slate-400">{{ ad.symbolrate }}</td>
              <td class="py-3 px-4 font-bold text-emerald-400">
                <div class="flex items-center gap-2">
                  <span>{{ ad.snr_pct }}</span>
                  <div class="w-16 h-1.5 bg-slate-800 rounded-full overflow-hidden">
                    <div class="h-full bg-emerald-400" :style="{ width: ad.snr_pct }"></div>
                  </div>
                </div>
              </td>
              <td class="py-3 px-4 text-slate-200 font-bold">{{ ad.snr_db }}</td>
              <td class="py-3 px-4 text-cyan-400">{{ ad.ber }}</td>
              <td class="py-3 px-4 text-right">
                <span class="text-[10px] bg-emerald-500/10 text-emerald-400 border border-emerald-500/30 px-2 py-0.5 rounded font-sans font-bold">
                  TUNER LOCK
                </span>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'

const adapters = ref([
  { id: '0', name: 'TBS 6904 Dual DVB-S2', freq: '11494 MHz (H)', symbolrate: '27500 KSym/s', snr_pct: '92.4%', snr_db: '14.2 dB', ber: '0' },
  { id: '1', name: 'TBS 6904 Dual DVB-S2', freq: '11747 MHz (V)', symbolrate: '30000 KSym/s', snr_pct: '94.0%', snr_db: '14.8 dB', ber: '1e-9' },
  { id: '2', name: 'TBS 6908 Quad DVB-S2', freq: '12054 MHz (R)', symbolrate: '27500 KSym/s', snr_pct: '90.8%', snr_db: '13.9 dB', ber: '0' },
  { id: '3', name: 'TBS 6908 Quad DVB-S2', freq: '12322 MHz (L)', symbolrate: '27500 KSym/s', snr_pct: '95.2%', snr_db: '15.1 dB', ber: '0' },
  { id: '4', name: 'TBS 6908 Quad DVB-S2', freq: '11044 MHz (H)', symbolrate: '30000 KSym/s', snr_pct: '93.1%', snr_db: '14.5 dB', ber: '0' },
  { id: '5', name: 'TBS 6908 Quad DVB-S2', freq: '11595 MHz (V)', symbolrate: '27500 KSym/s', snr_pct: '91.5%', snr_db: '14.0 dB', ber: '0' },
])
</script>
