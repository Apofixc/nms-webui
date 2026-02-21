<template>
  <div class="flex min-h-0 flex-1">
    <nav class="w-52 flex-shrink-0 border-r border-surface-700 bg-surface-800/80 p-3 overflow-y-auto">
      <h2 class="px-3 py-2 text-xs font-semibold uppercase tracking-wider text-slate-500">Настройки</h2>
      <ul class="space-y-0.5">
        <li v-for="item in navItems" :key="item.id">
          <button
            type="button"
            :class="[
              'w-full text-left px-3 py-2.5 rounded-lg text-sm font-medium transition-colors',
              activeNav === item.id
                ? 'bg-accent/15 text-accent'
                : 'text-slate-400 hover:text-white hover:bg-surface-700/50'
            ]"
            @click="activeNav = item.id"
          >
            {{ item.label }}
          </button>
        </li>
      </ul>
    </nav>

    <main class="flex-1 min-w-0 p-6 md:p-8 overflow-auto">
      <div v-if="loading && !settings" class="flex justify-center py-20">
        <div class="w-10 h-10 border-2 border-accent/40 border-t-accent rounded-full animate-spin" />
      </div>

      <template v-else>
        <div class="flex flex-wrap items-start justify-between gap-4 mb-6">
          <div>
            <h1 class="text-xl font-semibold text-white">{{ activeNavLabel }}</h1>
            <p class="text-sm text-slate-400 mt-0.5">{{ activeNavDescription }}</p>
          </div>
          <div v-if="activeNav !== 'stream'" class="flex items-center gap-3">
            <button
              type="button"
              :disabled="saving"
              class="rounded-lg px-4 py-2 text-sm font-medium bg-accent text-white hover:bg-accent/90 disabled:opacity-50 transition-colors"
              @click="save"
            >
              {{ saving ? 'Сохранение…' : 'Сохранить' }}
            </button>
            <p v-if="saveOk" class="text-sm text-green-400">Сохранено</p>
            <p v-if="saveError" class="text-sm text-danger">{{ saveError }}</p>
          </div>
          <div v-else class="flex items-center gap-3">
            <p v-if="saveOk" class="text-sm text-green-400">Сохранено</p>
            <p v-if="saveError" class="text-sm text-danger">{{ saveError }}</p>
          </div>
        </div>

        <div v-if="activeNav === 'stream'" class="space-y-8 max-w-2xl">
          <section class="rounded-xl border border-surface-700 bg-surface-800/60 overflow-hidden">
            <div class="px-5 py-4 border-b border-surface-700">
              <h3 class="text-base font-medium text-white">Захват кадра (превью)</h3>
              <p class="text-sm text-slate-400 mt-1">
                Программа для захвата одного кадра по URL потока (HTTP/UDP). Выбор бэкенда применяется сразу.
              </p>
              <div class="mt-2 text-xs text-slate-500">
                <span>Активный бэкенд: <span class="text-accent font-medium">{{ captureBackendLabel[form.modules.stream.capture.backend] || form.modules.stream.capture.backend }}</span></span>
                <span v-if="settings?.available?.capture?.length" class="ml-2">
                  Доступно в системе: {{ settings.available.capture.join(', ') }}
                </span>
              </div>
            </div>
            <div class="p-5 space-y-4">
              <div class="grid grid-cols-1 sm:grid-cols-[minmax(0,1fr)_auto] gap-2 sm:gap-4 items-center">
                <label class="text-sm text-slate-300">Бэкенд</label>
                <select
                  v-model="form.modules.stream.capture.backend"
                  class="bg-surface-700 border border-surface-600 rounded-lg px-4 py-2 text-white focus:ring-2 focus:ring-accent/50 w-full sm:w-56"
                  @change="save(true)"
                >
                  <option
                    v-for="opt in captureBackendOptions"
                    :key="opt.value"
                    :value="opt.value"
                  >
                    {{ opt.value === 'auto' ? opt.label : opt.label + (settings?.available?.capture?.includes(opt.value) ? ' (установлен)' : ' (не найден)') }}
                  </option>
                </select>
              </div>
              <div class="grid grid-cols-1 sm:grid-cols-[minmax(0,1fr)_auto] gap-2 sm:gap-4 items-center">
                <label class="text-sm text-slate-300">Таймаут (сек)</label>
                <input
                  v-model.number="form.modules.stream.capture.timeout_sec"
                  type="number"
                  min="1"
                  max="120"
                  step="1"
                  class="bg-surface-700 border border-surface-600 rounded-lg px-3 py-2 text-white w-full sm:w-24 focus:ring-2 focus:ring-accent/50"
                />
              </div>
              <div class="grid grid-cols-1 sm:grid-cols-[minmax(0,1fr)_auto] gap-2 sm:gap-4 items-center">
                <label class="text-sm text-slate-300">Качество JPEG (1–100)</label>
                <input
                  v-model="form.modules.stream.capture.jpeg_quality_input"
                  type="text"
                  placeholder="по умолчанию"
                  class="bg-surface-700 border border-surface-600 rounded-lg px-3 py-2 text-white w-full sm:w-28 focus:ring-2 focus:ring-accent/50 placeholder:text-slate-500"
                />
              </div>
              <div
                v-if="form.modules.stream.capture.backend !== 'auto'"
                class="pt-3 border-t border-surface-600"
              >
                <h4 class="text-sm font-medium text-slate-300 mb-3">Параметры выбранного бэкенда</h4>
                <template v-if="form.modules.stream.capture.backend === 'builtin'">
                  <p class="text-xs text-slate-500">Встроенный бэкенд не требует дополнительных параметров.</p>
                </template>
                <template v-else-if="form.modules.stream.capture.backend === 'ffmpeg'">
                  <div class="space-y-3">
                    <div class="grid grid-cols-1 sm:grid-cols-[minmax(0,1fr)_auto] gap-2 sm:gap-4 items-center">
                      <label class="text-sm text-slate-400">Путь к ffmpeg</label>
                      <input
                        v-model="form.modules.stream.capture.backends.ffmpeg.bin"
                        type="text"
                        placeholder="ffmpeg"
                        class="bg-surface-700 border border-surface-600 rounded-lg px-3 py-2 text-white w-full sm:w-48 focus:ring-2 focus:ring-accent/50 placeholder:text-slate-500"
                      />
                    </div>
                    <div class="grid grid-cols-1 sm:grid-cols-[minmax(0,1fr)_auto] gap-2 sm:gap-4 items-center">
                      <label class="text-sm text-slate-400">analyzeduration (µs)</label>
                      <input
                        v-model.number="form.modules.stream.capture.backends.ffmpeg.analyzeduration_us"
                        type="number"
                        min="10000"
                        max="30000000"
                        class="bg-surface-700 border border-surface-600 rounded-lg px-3 py-2 text-white w-full sm:w-32 focus:ring-2 focus:ring-accent/50"
                      />
                    </div>
                    <div class="grid grid-cols-1 sm:grid-cols-[minmax(0,1fr)_auto] gap-2 sm:gap-4 items-center">
                      <label class="text-sm text-slate-400">probesize (байт)</label>
                      <input
                        v-model.number="form.modules.stream.capture.backends.ffmpeg.probesize"
                        type="number"
                        min="10000"
                        max="50000000"
                        class="bg-surface-700 border border-surface-600 rounded-lg px-3 py-2 text-white w-full sm:w-32 focus:ring-2 focus:ring-accent/50"
                      />
                    </div>
                    <div class="grid grid-cols-1 sm:grid-cols-[minmax(0,1fr)_auto] gap-2 sm:gap-4 items-center">
                      <label class="text-sm text-slate-400">stimeout (µs, 0 = по умол.)</label>
                      <input
                        v-model.number="form.modules.stream.capture.backends.ffmpeg.stimeout_us"
                        type="number"
                        min="0"
                        max="60000000"
                        class="bg-surface-700 border border-surface-600 rounded-lg px-3 py-2 text-white w-full sm:w-32 focus:ring-2 focus:ring-accent/50"
                      />
                    </div>
                    <div class="grid grid-cols-1 sm:grid-cols-[minmax(0,1fr)_auto] gap-2 sm:gap-4 items-center">
                      <label class="text-sm text-slate-400">Доп. аргументы (ввод)</label>
                      <input
                        v-model="form.modules.stream.capture.backends.ffmpeg.extra_args"
                        type="text"
                        placeholder="—"
                        class="bg-surface-700 border border-surface-600 rounded-lg px-3 py-2 text-white w-full sm:w-64 focus:ring-2 focus:ring-accent/50 placeholder:text-slate-500"
                      />
                    </div>
                  </div>
                </template>
                <template v-else-if="form.modules.stream.capture.backend === 'vlc'">
                  <div class="space-y-3">
                    <div class="grid grid-cols-1 sm:grid-cols-[minmax(0,1fr)_auto] gap-2 sm:gap-4 items-center">
                      <label class="text-sm text-slate-400">Путь к vlc</label>
                      <input
                        v-model="form.modules.stream.capture.backends.vlc.bin"
                        type="text"
                        placeholder="vlc"
                        class="bg-surface-700 border border-surface-600 rounded-lg px-3 py-2 text-white w-full sm:w-48 focus:ring-2 focus:ring-accent/50 placeholder:text-slate-500"
                      />
                    </div>
                    <div class="grid grid-cols-1 sm:grid-cols-[minmax(0,1fr)_auto] gap-2 sm:gap-4 items-center">
                      <label class="text-sm text-slate-400">Время захвата (сек)</label>
                      <input
                        v-model.number="form.modules.stream.capture.backends.vlc.run_time_sec"
                        type="number"
                        min="1"
                        max="30"
                        class="bg-surface-700 border border-surface-600 rounded-lg px-3 py-2 text-white w-full sm:w-24 focus:ring-2 focus:ring-accent/50"
                      />
                    </div>
                    <div class="grid grid-cols-1 sm:grid-cols-[minmax(0,1fr)_auto] gap-2 sm:gap-4 items-center">
                      <label class="text-sm text-slate-400">scene-ratio</label>
                      <input
                        v-model.number="form.modules.stream.capture.backends.vlc.scene_ratio"
                        type="number"
                        min="1"
                        max="100"
                        class="bg-surface-700 border border-surface-600 rounded-lg px-3 py-2 text-white w-full sm:w-24 focus:ring-2 focus:ring-accent/50"
                      />
                    </div>
                    <div class="grid grid-cols-1 sm:grid-cols-[minmax(0,1fr)_auto] gap-2 sm:gap-4 items-center">
                      <label class="text-sm text-slate-400">Кэш сети (мс)</label>
                      <input
                        v-model.number="form.modules.stream.capture.backends.vlc.network_caching_ms"
                        type="number"
                        min="0"
                        max="60000"
                        class="bg-surface-700 border border-surface-600 rounded-lg px-3 py-2 text-white w-full sm:w-28 focus:ring-2 focus:ring-accent/50"
                      />
                    </div>
                  </div>
                </template>
                <template v-else-if="form.modules.stream.capture.backend === 'gstreamer'">
                  <div class="space-y-3">
                    <div class="grid grid-cols-1 sm:grid-cols-[minmax(0,1fr)_auto] gap-2 sm:gap-4 items-center">
                      <label class="text-sm text-slate-400">Путь к gst-launch</label>
                    <input
                      v-model="form.modules.stream.capture.backends.gstreamer.bin"
                      type="text"
                      placeholder="gst-launch-1.0"
                      class="bg-surface-700 border border-surface-600 rounded-lg px-3 py-2 text-white w-full sm:w-48 focus:ring-2 focus:ring-accent/50 placeholder:text-slate-500"
                    />
                    </div>
                    <div class="grid grid-cols-1 sm:grid-cols-[minmax(0,1fr)_auto] gap-2 sm:gap-4 items-center">
                      <label class="text-sm text-slate-400">buffer-size (байт, −1 = по умол.)</label>
                      <input
                        v-model.number="form.modules.stream.capture.backends.gstreamer.buffer_size"
                        type="number"
                        min="-1"
                        max="50000000"
                        class="bg-surface-700 border border-surface-600 rounded-lg px-3 py-2 text-white w-full sm:w-32 focus:ring-2 focus:ring-accent/50"
                      />
                    </div>
                  </div>
                </template>
              </div>
              <div class="pt-4 border-t border-surface-600 flex items-center gap-3">
                <button
                  type="button"
                  :disabled="saving"
                  class="rounded-lg px-4 py-2 text-sm font-medium bg-accent text-white hover:bg-accent/90 disabled:opacity-50 transition-colors"
                  @click="save()"
                >
                  {{ saving ? 'Сохранение…' : 'Сохранить' }}
                </button>
                <p v-if="saveOk" class="text-sm text-green-400">Сохранено</p>
                <p v-if="saveError" class="text-sm text-danger">{{ saveError }}</p>
              </div>
            </div>
          </section>

          <section class="rounded-xl border border-surface-700 bg-surface-800/60 overflow-hidden">
            <div class="px-5 py-4 border-b border-surface-700">
              <h3 class="text-base font-medium text-white">Воспроизведение потоков</h3>
              <p class="text-sm text-slate-400 mt-1">
                Универсальный конвертер: вход (UDP, HTTP, RTP, RTSP, SRT, HLS, TCP, файл) → вывод в браузер: HTTP TS (сырой MPEG-TS), HLS или WebRTC (WHEP). Выбор бэкенда и формата применяется сразу.
              </p>
              <div class="mt-2 text-xs text-slate-500">
                <span>Активный бэкенд: <span class="text-accent font-medium">{{ playbackBackendLabel[form.modules.stream.playback_udp.backend] || form.modules.stream.playback_udp.backend }}</span></span>
                <span class="ml-3">Формат вывода: <span class="text-accent font-medium">{{ outputFormatLabel[form.modules.stream.playback_udp.output_format] || form.modules.stream.playback_udp.output_format }}</span></span>
              </div>
              <div v-if="settings?.available?.playback_udp?.length" class="mt-1 text-xs text-slate-500">
                Доступно в системе: {{ settings.available.playback_udp.join(', ') }}
              </div>
            </div>
            <div class="p-5 space-y-4">
              <div class="grid grid-cols-1 sm:grid-cols-[minmax(0,1fr)_auto] gap-2 sm:gap-4 items-center">
                <label class="text-sm text-slate-300">Бэкенд</label>
                <select
                  v-model="form.modules.stream.playback_udp.backend"
                  class="bg-surface-700 border border-surface-600 rounded-lg px-4 py-2 text-white w-full sm:w-56 focus:ring-2 focus:ring-accent/50"
                  @change="save(true)"
                >
                  <option
                    v-for="opt in playbackBackendOptionsFiltered"
                    :key="opt.value"
                    :value="opt.value"
                  >
                    {{ opt.value === 'auto' ? opt.label : opt.value === 'udp_proxy' ? opt.label + ' (всегда)' : opt.label + (settings?.available?.playback_udp?.includes(opt.value) ? ' (установлен)' : ' (не найден)') }}
                  </option>
                </select>
              </div>
              <div class="grid grid-cols-1 sm:grid-cols-[minmax(0,1fr)_auto] gap-2 sm:gap-4 items-center">
                <label class="text-sm text-slate-300">Формат вывода</label>
                <select
                  v-model="form.modules.stream.playback_udp.output_format"
                  class="bg-surface-700 border border-surface-600 rounded-lg px-4 py-2 text-white w-full sm:w-56 focus:ring-2 focus:ring-accent/50"
                  @change="save(true)"
                >
                  <option
                    v-for="opt in outputFormatOptionsForBackend"
                    :key="opt.value"
                    :value="opt.value"
                  >
                    {{ opt.label }}
                  </option>
                </select>
                <p v-if="form.modules.stream.playback_udp.backend !== 'auto'" class="sm:col-span-2 text-xs text-slate-500">
                  Для выбранного бэкенда доступны только эти форматы вывода.
                </p>
              </div>
              <div
                v-if="form.modules.stream.playback_udp.backend !== 'auto'"
                class="pt-3 border-t border-surface-600"
              >
                <h4 class="text-sm font-medium text-slate-300 mb-3">Параметры по бэкендам</h4>
                <p v-if="streamLinksForBackend.length" class="text-xs text-slate-500 mb-2">
                  Связки для выбранного бэкенда: {{ streamLinksForBackend.join(', ') }}
                </p>
                <p class="text-xs text-slate-500 mb-3">
                  {{ form.modules.stream.playback_udp.output_format === 'hls' ? 'Параметры для вывода HLS.' : form.modules.stream.playback_udp.output_format === 'webrtc' ? 'WebRTC (WHEP) — в разработке.' : 'Параметры для вывода HTTP TS.' }}
                </p>
                <p
                  v-if="form.modules.stream.playback_udp.output_format === 'hls' && ['astra', 'udp_proxy'].includes(form.modules.stream.playback_udp.backend)"
                  class="text-sm text-amber-400"
                >
                  Выбранный бэкенд не поддерживает HLS. Для HLS доступны FFmpeg, VLC, GStreamer, TSDuck.
                </p>
                <div
                  v-else-if="form.modules.stream.playback_udp.backend === 'ffmpeg' && form.modules.stream.playback_udp.output_format === 'http_ts'"
                  class="space-y-3"
                >
                  <div class="grid grid-cols-1 sm:grid-cols-[minmax(0,1fr)_auto] gap-2 sm:gap-4 items-center">
                    <label class="text-sm text-slate-400">Путь к ffmpeg</label>
                    <input
                      v-model="form.modules.stream.playback_udp.backends.ffmpeg.bin"
                      type="text"
                      placeholder="ffmpeg"
                      class="bg-surface-700 border border-surface-600 rounded-lg px-3 py-2 text-white w-full sm:w-48 focus:ring-2 focus:ring-accent/50 placeholder:text-slate-500"
                    />
                  </div>
                  <div class="grid grid-cols-1 sm:grid-cols-[minmax(0,1fr)_auto] gap-2 sm:gap-4 items-center">
                    <label class="text-sm text-slate-400">Буфер (КБ)</label>
                    <input
                      v-model.number="form.modules.stream.playback_udp.backends.ffmpeg.buffer_kb"
                      type="number"
                      min="64"
                      max="65536"
                      class="bg-surface-700 border border-surface-600 rounded-lg px-3 py-2 text-white w-full sm:w-28 focus:ring-2 focus:ring-accent/50"
                    />
                  </div>
                  <div class="grid grid-cols-1 sm:grid-cols-[minmax(0,1fr)_auto] gap-2 sm:gap-4 items-center">
                    <label class="text-sm text-slate-400">analyzeduration (µs)</label>
                    <input
                      v-model.number="form.modules.stream.playback_udp.backends.ffmpeg.analyzeduration_us"
                      type="number"
                      min="10000"
                      max="30000000"
                      class="bg-surface-700 border border-surface-600 rounded-lg px-3 py-2 text-white w-full sm:w-32 focus:ring-2 focus:ring-accent/50"
                    />
                  </div>
                  <div class="grid grid-cols-1 sm:grid-cols-[minmax(0,1fr)_auto] gap-2 sm:gap-4 items-center">
                    <label class="text-sm text-slate-400">probesize (байт)</label>
                    <input
                      v-model.number="form.modules.stream.playback_udp.backends.ffmpeg.probesize"
                      type="number"
                      min="10000"
                      max="50000000"
                      class="bg-surface-700 border border-surface-600 rounded-lg px-3 py-2 text-white w-full sm:w-32 focus:ring-2 focus:ring-accent/50"
                    />
                  </div>
                  <div class="grid grid-cols-1 sm:grid-cols-[minmax(0,1fr)_auto] gap-2 sm:gap-4 items-center">
                    <label class="text-sm text-slate-400">Доп. аргументы</label>
                    <input
                      v-model="form.modules.stream.playback_udp.backends.ffmpeg.extra_args"
                      type="text"
                      placeholder="—"
                      class="bg-surface-700 border border-surface-600 rounded-lg px-3 py-2 text-white w-full sm:w-64 focus:ring-2 focus:ring-accent/50 placeholder:text-slate-500"
                    />
                  </div>
                </div>
                <div
                  v-else-if="form.modules.stream.playback_udp.backend === 'ffmpeg' && form.modules.stream.playback_udp.output_format === 'hls'"
                  class="space-y-3"
                >
                  <div class="grid grid-cols-1 sm:grid-cols-[minmax(0,1fr)_auto] gap-2 sm:gap-4 items-center">
                    <label class="text-sm text-slate-400">Путь к ffmpeg</label>
                    <input
                      v-model="form.modules.stream.playback_udp.backends.ffmpeg.bin"
                      type="text"
                      placeholder="ffmpeg"
                      class="bg-surface-700 border border-surface-600 rounded-lg px-3 py-2 text-white w-full sm:w-48 focus:ring-2 focus:ring-accent/50 placeholder:text-slate-500"
                    />
                  </div>
                  <div class="grid grid-cols-1 sm:grid-cols-[minmax(0,1fr)_auto] gap-2 sm:gap-4 items-center">
                    <label class="text-sm text-slate-400">hls_time (с)</label>
                    <input
                      v-model.number="form.modules.stream.playback_udp.backends.ffmpeg.hls_time"
                      type="number"
                      min="1"
                      max="30"
                      class="bg-surface-700 border border-surface-600 rounded-lg px-3 py-2 text-white w-full sm:w-28 focus:ring-2 focus:ring-accent/50"
                    />
                  </div>
                  <div class="grid grid-cols-1 sm:grid-cols-[minmax(0,1fr)_auto] gap-2 sm:gap-4 items-center">
                    <label class="text-sm text-slate-400">hls_list_size</label>
                    <input
                      v-model.number="form.modules.stream.playback_udp.backends.ffmpeg.hls_list_size"
                      type="number"
                      min="2"
                      max="30"
                      class="bg-surface-700 border border-surface-600 rounded-lg px-3 py-2 text-white w-full sm:w-28 focus:ring-2 focus:ring-accent/50"
                    />
                  </div>
                  <div class="grid grid-cols-1 sm:grid-cols-[minmax(0,1fr)_auto] gap-2 sm:gap-4 items-center">
                    <label class="text-sm text-slate-400">analyzeduration (µs)</label>
                    <input
                      v-model.number="form.modules.stream.playback_udp.backends.ffmpeg.analyzeduration_us"
                      type="number"
                      min="10000"
                      max="30000000"
                      class="bg-surface-700 border border-surface-600 rounded-lg px-3 py-2 text-white w-full sm:w-32 focus:ring-2 focus:ring-accent/50"
                    />
                  </div>
                  <div class="grid grid-cols-1 sm:grid-cols-[minmax(0,1fr)_auto] gap-2 sm:gap-4 items-center">
                    <label class="text-sm text-slate-400">probesize (байт)</label>
                    <input
                      v-model.number="form.modules.stream.playback_udp.backends.ffmpeg.probesize"
                      type="number"
                      min="10000"
                      max="50000000"
                      class="bg-surface-700 border border-surface-600 rounded-lg px-3 py-2 text-white w-full sm:w-32 focus:ring-2 focus:ring-accent/50"
                    />
                  </div>
                  <div class="grid grid-cols-1 sm:grid-cols-[minmax(0,1fr)_auto] gap-2 sm:gap-4 items-center">
                    <label class="text-sm text-slate-400">Доп. аргументы</label>
                    <input
                      v-model="form.modules.stream.playback_udp.backends.ffmpeg.extra_args"
                      type="text"
                      placeholder="—"
                      class="bg-surface-700 border border-surface-600 rounded-lg px-3 py-2 text-white w-full sm:w-64 focus:ring-2 focus:ring-accent/50 placeholder:text-slate-500"
                    />
                  </div>
                </div>
                <div
                  v-else-if="form.modules.stream.playback_udp.backend === 'vlc' && form.modules.stream.playback_udp.output_format === 'http_ts'"
                  class="space-y-3"
                >
                  <div class="grid grid-cols-1 sm:grid-cols-[minmax(0,1fr)_auto] gap-2 sm:gap-4 items-center">
                    <label class="text-sm text-slate-400">Путь к vlc</label>
                    <input
                      v-model="form.modules.stream.playback_udp.backends.vlc.bin"
                      type="text"
                      placeholder="vlc"
                      class="bg-surface-700 border border-surface-600 rounded-lg px-3 py-2 text-white w-full sm:w-48 focus:ring-2 focus:ring-accent/50 placeholder:text-slate-500"
                    />
                  </div>
                  <div class="grid grid-cols-1 sm:grid-cols-[minmax(0,1fr)_auto] gap-2 sm:gap-4 items-center">
                    <label class="text-sm text-slate-400">Буфер (КБ)</label>
                    <input
                      v-model.number="form.modules.stream.playback_udp.backends.vlc.buffer_kb"
                      type="number"
                      min="64"
                      max="65536"
                      class="bg-surface-700 border border-surface-600 rounded-lg px-3 py-2 text-white w-full sm:w-28 focus:ring-2 focus:ring-accent/50"
                    />
                  </div>
                </div>
                <div
                  v-else-if="form.modules.stream.playback_udp.backend === 'vlc' && form.modules.stream.playback_udp.output_format === 'hls'"
                  class="space-y-3"
                >
                  <div class="grid grid-cols-1 sm:grid-cols-[minmax(0,1fr)_auto] gap-2 sm:gap-4 items-center">
                    <label class="text-sm text-slate-400">Путь к vlc</label>
                    <input
                      v-model="form.modules.stream.playback_udp.backends.vlc.bin"
                      type="text"
                      placeholder="vlc"
                      class="bg-surface-700 border border-surface-600 rounded-lg px-3 py-2 text-white w-full sm:w-48 focus:ring-2 focus:ring-accent/50 placeholder:text-slate-500"
                    />
                  </div>
                  <div class="grid grid-cols-1 sm:grid-cols-[minmax(0,1fr)_auto] gap-2 sm:gap-4 items-center">
                    <label class="text-sm text-slate-400">hls_time (с)</label>
                    <input
                      v-model.number="form.modules.stream.playback_udp.backends.vlc.hls_time"
                      type="number"
                      min="1"
                      max="30"
                      class="bg-surface-700 border border-surface-600 rounded-lg px-3 py-2 text-white w-full sm:w-28 focus:ring-2 focus:ring-accent/50"
                    />
                  </div>
                  <div class="grid grid-cols-1 sm:grid-cols-[minmax(0,1fr)_auto] gap-2 sm:gap-4 items-center">
                    <label class="text-sm text-slate-400">hls_list_size</label>
                    <input
                      v-model.number="form.modules.stream.playback_udp.backends.vlc.hls_list_size"
                      type="number"
                      min="2"
                      max="30"
                      class="bg-surface-700 border border-surface-600 rounded-lg px-3 py-2 text-white w-full sm:w-28 focus:ring-2 focus:ring-accent/50"
                    />
                  </div>
                </div>
                <div
                  v-else-if="form.modules.stream.playback_udp.backend === 'gstreamer' && form.modules.stream.playback_udp.output_format === 'http_ts'"
                  class="space-y-3"
                >
                  <div class="grid grid-cols-1 sm:grid-cols-[minmax(0,1fr)_auto] gap-2 sm:gap-4 items-center">
                    <label class="text-sm text-slate-400">Путь к gst-launch</label>
                    <input
                      v-model="form.modules.stream.playback_udp.backends.gstreamer.bin"
                      type="text"
                      placeholder="gst-launch-1.0"
                      class="bg-surface-700 border border-surface-600 rounded-lg px-3 py-2 text-white w-full sm:w-48 focus:ring-2 focus:ring-accent/50 placeholder:text-slate-500"
                    />
                  </div>
                  <div class="grid grid-cols-1 sm:grid-cols-[minmax(0,1fr)_auto] gap-2 sm:gap-4 items-center">
                    <label class="text-sm text-slate-400">Буфер (КБ)</label>
                    <input
                      v-model.number="form.modules.stream.playback_udp.backends.gstreamer.buffer_kb"
                      type="number"
                      min="64"
                      max="65536"
                      class="bg-surface-700 border border-surface-600 rounded-lg px-3 py-2 text-white w-full sm:w-28 focus:ring-2 focus:ring-accent/50"
                    />
                  </div>
                </div>
                <div
                  v-else-if="form.modules.stream.playback_udp.backend === 'gstreamer' && form.modules.stream.playback_udp.output_format === 'hls'"
                  class="space-y-3"
                >
                  <div class="grid grid-cols-1 sm:grid-cols-[minmax(0,1fr)_auto] gap-2 sm:gap-4 items-center">
                    <label class="text-sm text-slate-400">Путь к gst-launch</label>
                    <input
                      v-model="form.modules.stream.playback_udp.backends.gstreamer.bin"
                      type="text"
                      placeholder="gst-launch-1.0"
                      class="bg-surface-700 border border-surface-600 rounded-lg px-3 py-2 text-white w-full sm:w-48 focus:ring-2 focus:ring-accent/50 placeholder:text-slate-500"
                    />
                  </div>
                  <div class="grid grid-cols-1 sm:grid-cols-[minmax(0,1fr)_auto] gap-2 sm:gap-4 items-center">
                    <label class="text-sm text-slate-400">hls_time (с)</label>
                    <input
                      v-model.number="form.modules.stream.playback_udp.backends.gstreamer.hls_time"
                      type="number"
                      min="1"
                      max="30"
                      class="bg-surface-700 border border-surface-600 rounded-lg px-3 py-2 text-white w-full sm:w-28 focus:ring-2 focus:ring-accent/50"
                    />
                  </div>
                  <div class="grid grid-cols-1 sm:grid-cols-[minmax(0,1fr)_auto] gap-2 sm:gap-4 items-center">
                    <label class="text-sm text-slate-400">hls_list_size</label>
                    <input
                      v-model.number="form.modules.stream.playback_udp.backends.gstreamer.hls_list_size"
                      type="number"
                      min="2"
                      max="30"
                      class="bg-surface-700 border border-surface-600 rounded-lg px-3 py-2 text-white w-full sm:w-28 focus:ring-2 focus:ring-accent/50"
                    />
                  </div>
                </div>
                <div
                  v-else-if="form.modules.stream.playback_udp.backend === 'tsduck' && form.modules.stream.playback_udp.output_format === 'http_ts'"
                  class="space-y-3"
                >
                  <div class="grid grid-cols-1 sm:grid-cols-[minmax(0,1fr)_auto] gap-2 sm:gap-4 items-center">
                    <label class="text-sm text-slate-400">Путь к tsp</label>
                    <input
                      v-model="form.modules.stream.playback_udp.backends.tsduck.bin"
                      type="text"
                      placeholder="tsp"
                      class="bg-surface-700 border border-surface-600 rounded-lg px-3 py-2 text-white w-full sm:w-48 focus:ring-2 focus:ring-accent/50 placeholder:text-slate-500"
                    />
                  </div>
                  <div class="grid grid-cols-1 sm:grid-cols-[minmax(0,1fr)_auto] gap-2 sm:gap-4 items-center">
                    <label class="text-sm text-slate-400">Буфер (КБ)</label>
                    <input
                      v-model.number="form.modules.stream.playback_udp.backends.tsduck.buffer_kb"
                      type="number"
                      min="64"
                      max="65536"
                      class="bg-surface-700 border border-surface-600 rounded-lg px-3 py-2 text-white w-full sm:w-28 focus:ring-2 focus:ring-accent/50"
                    />
                  </div>
                </div>
                <div
                  v-else-if="form.modules.stream.playback_udp.backend === 'tsduck' && form.modules.stream.playback_udp.output_format === 'hls'"
                  class="space-y-3"
                >
                  <div class="grid grid-cols-1 sm:grid-cols-[minmax(0,1fr)_auto] gap-2 sm:gap-4 items-center">
                    <label class="text-sm text-slate-400">Путь к tsp</label>
                    <input
                      v-model="form.modules.stream.playback_udp.backends.tsduck.bin"
                      type="text"
                      placeholder="tsp"
                      class="bg-surface-700 border border-surface-600 rounded-lg px-3 py-2 text-white w-full sm:w-48 focus:ring-2 focus:ring-accent/50 placeholder:text-slate-500"
                    />
                  </div>
                  <div class="grid grid-cols-1 sm:grid-cols-[minmax(0,1fr)_auto] gap-2 sm:gap-4 items-center">
                    <label class="text-sm text-slate-400">hls_time (с)</label>
                    <input
                      v-model.number="form.modules.stream.playback_udp.backends.tsduck.hls_time"
                      type="number"
                      min="1"
                      max="30"
                      class="bg-surface-700 border border-surface-600 rounded-lg px-3 py-2 text-white w-full sm:w-28 focus:ring-2 focus:ring-accent/50"
                    />
                  </div>
                  <div class="grid grid-cols-1 sm:grid-cols-[minmax(0,1fr)_auto] gap-2 sm:gap-4 items-center">
                    <label class="text-sm text-slate-400">hls_list_size</label>
                    <input
                      v-model.number="form.modules.stream.playback_udp.backends.tsduck.hls_list_size"
                      type="number"
                      min="2"
                      max="30"
                      class="bg-surface-700 border border-surface-600 rounded-lg px-3 py-2 text-white w-full sm:w-28 focus:ring-2 focus:ring-accent/50"
                    />
                  </div>
                </div>
                <p
                  v-else-if="form.modules.stream.playback_udp.backend === 'udp_proxy' && form.modules.stream.playback_udp.output_format === 'http_ts'"
                  class="text-xs text-slate-500"
                >
                  Встроенный UDP→HTTP прокси. Дополнительные параметры не требуются.
                </p>
                <div
                  v-else-if="form.modules.stream.playback_udp.backend === 'webrtc' && form.modules.stream.playback_udp.output_format === 'webrtc'"
                  class="space-y-3"
                >
                  <p class="text-xs text-slate-500 mb-2">
                    Параметры для вывода WebRTC (WHEP). Опции STUN/TURN при необходимости настраиваются на сервере.
                  </p>
                </div>
                <div
                  v-else-if="form.modules.stream.playback_udp.backend === 'astra' && form.modules.stream.playback_udp.output_format === 'http_ts'"
                  class="space-y-3"
                >
                  <p class="text-xs text-slate-500 mb-2">
                    Astra Relay (astra --relay -p PORT). Укажите базовый URL реле.
                  </p>
                  <div class="grid grid-cols-1 sm:grid-cols-[minmax(0,1fr)_auto] gap-2 sm:gap-4 items-center">
                    <label class="text-sm text-slate-400">URL реле</label>
                    <input
                      v-model="form.modules.stream.playback_udp.backends.astra.relay_url"
                      type="text"
                      placeholder="http://localhost:8000"
                      class="bg-surface-700 border border-surface-600 rounded-lg px-3 py-2 text-white w-full sm:w-72 focus:ring-2 focus:ring-accent/50 placeholder:text-slate-500"
                    />
                  </div>
                </div>
                <div v-if="hasPlaybackParamsToSave" class="pt-4 border-t border-surface-600 flex items-center gap-3">
                  <button
                    type="button"
                    :disabled="saving"
                    class="rounded-lg px-4 py-2 text-sm font-medium bg-accent text-white hover:bg-accent/90 disabled:opacity-50 transition-colors"
                    @click="save()"
                  >
                    {{ saving ? 'Сохранение…' : 'Сохранить' }}
                  </button>
                  <p v-if="saveOk" class="text-sm text-green-400">Сохранено</p>
                  <p v-if="saveError" class="text-sm text-danger">{{ saveError }}</p>
                </div>
              </div>
            </div>
          </section>
        </div>
      </template>
    </main>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import api from '../api'

const navItems = [
  { id: 'stream', label: 'Потоки', description: 'Превью каналов (картинки) и воспроизведение UDP.' },
]
const activeNav = ref('stream')

const activeNavLabel = computed(() => navItems.find((i) => i.id === activeNav.value)?.label ?? 'Настройки')
const activeNavDescription = computed(() => navItems.find((i) => i.id === activeNav.value)?.description ?? '')

const streamLinksForBackend = computed(() => {
  const links = settings.value?.stream_links
  const backend = form.value?.modules?.stream?.playback_udp?.backend
  if (!Array.isArray(links) || !backend || backend === 'auto') return []
  const outLabel = (f) => (f === 'http_hls' ? 'HLS' : f === 'http_ts' ? 'HTTP TS' : f === 'webrtc' ? 'WebRTC' : f)
  const inLabel = (f) => (f === 'udp' ? 'UDP' : f === 'http' ? 'HTTP' : f === 'rtp' ? 'RTP' : f === 'file' ? 'File' : f)
  return links
    .filter((l) => l.backend === backend)
    .map((l) => `${inLabel(l.input_format)} → ${outLabel(l.output_format)}`)
})

const loading = ref(true)
const settings = ref(null)
const form = ref({
  modules: {
    stream: {
      capture: {
        backend: 'auto',
        timeout_sec: 10,
        jpeg_quality: 90,
        jpeg_quality_input: '90',
        backends: {
          ffmpeg: { bin: 'ffmpeg', analyzeduration_us: 500000, probesize: 500000, stimeout_us: 0, extra_args: '' },
          vlc: { bin: 'vlc', run_time_sec: 2, scene_ratio: 1, network_caching_ms: 1000 },
          gstreamer: { bin: 'gst-launch-1.0', buffer_size: -1 },
        },
      },
      playback_udp: {
        backend: 'auto',
        output_format: 'http_ts',
        backends: {
          ffmpeg: { bin: 'ffmpeg', buffer_kb: 1024, extra_args: '', analyzeduration_us: 500000, probesize: 500000, hls_time: 2, hls_list_size: 5 },
          vlc: { bin: 'vlc', buffer_kb: 1024, hls_time: 2, hls_list_size: 5 },
          gstreamer: { bin: 'gst-launch-1.0', buffer_kb: 1024, hls_time: 2, hls_list_size: 5 },
          tsduck: { bin: 'tsp', buffer_kb: 1024, hls_time: 2, hls_list_size: 5 },
          astra: { relay_url: 'http://localhost:8000' },
          webrtc: {},
        },
      },
    },
  },
})
const captureBackendOptions = [
  { value: 'auto', label: 'Авто' },
  { value: 'builtin', label: 'Встроенный (без внешних программ)' },
  { value: 'ffmpeg', label: 'FFmpeg' },
  { value: 'vlc', label: 'VLC' },
  { value: 'gstreamer', label: 'GStreamer' },
]
const captureBackendLabel = Object.fromEntries(captureBackendOptions.map((o) => [o.value, o.label]))

const hasPlaybackParamsToSave = computed(() => {
  const backend = form.value?.modules?.stream?.playback_udp?.backend
  const out = form.value?.modules?.stream?.playback_udp?.output_format
  if (!backend || backend === 'auto') return false
  if (backend === 'udp_proxy' || backend === 'webrtc') return false
  return ['ffmpeg', 'vlc', 'gstreamer', 'tsduck', 'astra'].includes(backend)
})
const playbackUdpBackendOptions = [
  { value: 'auto', label: 'Авто' },
  { value: 'ffmpeg', label: 'FFmpeg' },
  { value: 'vlc', label: 'VLC' },
  { value: 'astra', label: 'Astra' },
  { value: 'gstreamer', label: 'GStreamer' },
  { value: 'tsduck', label: 'TSDuck' },
  { value: 'udp_proxy', label: 'Встроенный UDP→HTTP прокси' },
  { value: 'webrtc', label: 'WebRTC (WHEP)' },
]
const playbackBackendLabel = Object.fromEntries(playbackUdpBackendOptions.map((o) => [o.value, o.label]))

const OUTPUT_FORMAT_OPTIONS = [
  { value: 'http_ts', label: 'HTTP TS (сырой MPEG-TS)' },
  { value: 'hls', label: 'HLS (playlist.m3u8)' },
  { value: 'webrtc', label: 'WebRTC (WHEP)' },
]
const outputFormatLabel = Object.fromEntries(OUTPUT_FORMAT_OPTIONS.map((o) => [o.value, o.label]))

const outputFormatOptionsForBackend = computed(() => {
  const backend = form.value?.modules?.stream?.playback_udp?.backend
  if (!backend || backend === 'auto') return OUTPUT_FORMAT_OPTIONS
  const links = settings.value?.stream_links ?? []
  const supported = [...new Set(
    links.filter((l) => l.backend === backend).map((l) => l.output_format === 'http_hls' ? 'hls' : l.output_format)
  )]
  if (supported.length === 0) return OUTPUT_FORMAT_OPTIONS
  return OUTPUT_FORMAT_OPTIONS.filter((opt) => supported.includes(opt.value))
})

const playbackBackendOptionsFiltered = computed(() => {
  const out = form.value?.modules?.stream?.playback_udp?.output_format ?? 'http_ts'
  const byOut = settings.value?.playback_backends_by_output
  const list = byOut && Array.isArray(byOut[out]) ? byOut[out] : null
  const options = [{ value: 'auto', label: 'Авто' }]
  if (list && list.length) {
    list.forEach((b) => {
      const label = playbackBackendLabel[b] ?? b
      options.push({ value: b, label })
    })
  } else {
    playbackUdpBackendOptions.slice(1).forEach((o) => options.push(o))
  }
  return options
})

watch(
  () => form.value?.modules?.stream?.playback_udp?.output_format,
  (out) => {
    const backend = form.value?.modules?.stream?.playback_udp?.backend
    if (backend === 'auto' || !out) return
    const byOut = settings.value?.playback_backends_by_output
    const list = byOut?.[out]
    if (Array.isArray(list) && !list.includes(backend)) {
      form.value.modules.stream.playback_udp.backend = 'auto'
    }
  }
)

watch(
  () => form.value?.modules?.stream?.playback_udp?.backend,
  (backend) => {
    const out = form.value?.modules?.stream?.playback_udp?.output_format
    if (!out) return
    const opts = outputFormatOptionsForBackend.value
    const allowed = opts.map((o) => o.value)
    if (allowed.length && !allowed.includes(out)) {
      form.value.modules.stream.playback_udp.output_format = allowed[0]
      save(true)
    }
  }
)

const saving = ref(false)
const saveOk = ref(false)
const saveError = ref('')

function formFromModules(modules) {
  const stream = modules?.stream ?? {}
  const cap = stream.capture ?? {}
  const jq = cap.jpeg_quality
  const capBackends = cap.backends ?? {}
  const pb = stream.playback_udp ?? {}
  const pbBackends = pb.backends ?? {}
  return {
    modules: {
      stream: {
        capture: {
          backend: cap.backend ?? 'auto',
          timeout_sec: cap.timeout_sec ?? 10,
          jpeg_quality: jq ?? null,
          jpeg_quality_input: jq != null ? String(jq) : '',
          backends: {
            ffmpeg: {
              bin: (capBackends.ffmpeg ?? {}).bin ?? 'ffmpeg',
              analyzeduration_us: (capBackends.ffmpeg ?? {}).analyzeduration_us ?? 500000,
              probesize: (capBackends.ffmpeg ?? {}).probesize ?? 500000,
              stimeout_us: (capBackends.ffmpeg ?? {}).stimeout_us ?? 0,
              extra_args: (capBackends.ffmpeg ?? {}).extra_args ?? '',
            },
            vlc: {
              bin: (capBackends.vlc ?? {}).bin ?? 'vlc',
              run_time_sec: (capBackends.vlc ?? {}).run_time_sec ?? 2,
              scene_ratio: (capBackends.vlc ?? {}).scene_ratio ?? 1,
              network_caching_ms: (capBackends.vlc ?? {}).network_caching_ms ?? 1000,
            },
            gstreamer: {
              bin: (capBackends.gstreamer ?? {}).bin ?? 'gst-launch-1.0',
              buffer_size: (capBackends.gstreamer ?? {}).buffer_size ?? -1,
            },
          },
        },
        playback_udp: {
          backend: pb.backend ?? 'auto',
          output_format: pb.output_format ?? 'http_ts',
          backends: {
            ffmpeg: {
              bin: (pbBackends.ffmpeg ?? {}).bin ?? 'ffmpeg',
              buffer_kb: (pbBackends.ffmpeg ?? {}).buffer_kb ?? 1024,
              extra_args: (pbBackends.ffmpeg ?? {}).extra_args ?? '',
              analyzeduration_us: (pbBackends.ffmpeg ?? {}).analyzeduration_us ?? 500000,
              probesize: (pbBackends.ffmpeg ?? {}).probesize ?? 500000,
              hls_time: (pbBackends.ffmpeg ?? {}).hls_time ?? 2,
              hls_list_size: (pbBackends.ffmpeg ?? {}).hls_list_size ?? 5,
            },
            vlc: {
              bin: (pbBackends.vlc ?? {}).bin ?? 'vlc',
              buffer_kb: (pbBackends.vlc ?? {}).buffer_kb ?? 1024,
              hls_time: (pbBackends.vlc ?? {}).hls_time ?? 2,
              hls_list_size: (pbBackends.vlc ?? {}).hls_list_size ?? 5,
            },
            gstreamer: {
              bin: (pbBackends.gstreamer ?? {}).bin ?? 'gst-launch-1.0',
              buffer_kb: (pbBackends.gstreamer ?? {}).buffer_kb ?? 1024,
              hls_time: (pbBackends.gstreamer ?? {}).hls_time ?? 2,
              hls_list_size: (pbBackends.gstreamer ?? {}).hls_list_size ?? 5,
            },
            tsduck: {
              bin: (pbBackends.tsduck ?? {}).bin ?? 'tsp',
              buffer_kb: (pbBackends.tsduck ?? {}).buffer_kb ?? 1024,
              hls_time: (pbBackends.tsduck ?? {}).hls_time ?? 2,
              hls_list_size: (pbBackends.tsduck ?? {}).hls_list_size ?? 5,
            },
            astra: { relay_url: (pbBackends.astra ?? {}).relay_url ?? 'http://localhost:8000' },
            webrtc: pbBackends.webrtc ?? {},
          },
        },
      },
    },
  }
}

function formToModules() {
  const cap = form.value.modules.stream.capture
  let jq = cap.jpeg_quality
  const inp = (cap.jpeg_quality_input || '').trim()
  if (inp !== '') {
    const n = parseInt(inp, 10)
    jq = Number.isNaN(n) ? null : Math.max(1, Math.min(100, n))
  }
  const pb = form.value.modules.stream.playback_udp
  return {
    stream: {
      capture: {
        backend: cap.backend,
        timeout_sec: Math.max(1, Math.min(120, Number(cap.timeout_sec) || 10)),
        jpeg_quality: jq,
        backends: {
          ffmpeg: {
            bin: (cap.backends?.ffmpeg?.bin || 'ffmpeg').trim() || 'ffmpeg',
            analyzeduration_us: Math.max(10000, Math.min(30_000_000, Number(cap.backends?.ffmpeg?.analyzeduration_us) || 500000)),
            probesize: Math.max(10000, Math.min(50_000_000, Number(cap.backends?.ffmpeg?.probesize) || 500000)),
            stimeout_us: Math.max(0, Math.min(60_000_000, Number(cap.backends?.ffmpeg?.stimeout_us) || 0)),
            extra_args: typeof cap.backends?.ffmpeg?.extra_args === 'string' ? cap.backends.ffmpeg.extra_args : '',
          },
          vlc: {
            bin: (cap.backends?.vlc?.bin || 'vlc').trim() || 'vlc',
            run_time_sec: Math.max(1, Math.min(30, Number(cap.backends?.vlc?.run_time_sec) || 2)),
            scene_ratio: Math.max(1, Math.min(100, Number(cap.backends?.vlc?.scene_ratio) || 1)),
            network_caching_ms: Math.max(0, Math.min(60000, Number(cap.backends?.vlc?.network_caching_ms) || 1000)),
          },
          gstreamer: {
            bin: (cap.backends?.gstreamer?.bin || 'gst-launch-1.0').trim() || 'gst-launch-1.0',
            buffer_size: (() => {
              const v = Number(cap.backends?.gstreamer?.buffer_size);
              if (Number.isNaN(v) || v < -1) return -1;
              return v > 50_000_000 ? 50_000_000 : Math.round(v);
            })(),
          },
        },
      },
      playback_udp: {
        backend: pb.backend,
        output_format: pb.output_format || 'http_ts',
        backends: {
          ffmpeg: {
            bin: (pb.backends?.ffmpeg?.bin || 'ffmpeg').trim() || 'ffmpeg',
            buffer_kb: Math.max(64, Math.min(65536, Number(pb.backends?.ffmpeg?.buffer_kb) || 1024)),
            extra_args: typeof pb.backends?.ffmpeg?.extra_args === 'string' ? pb.backends.ffmpeg.extra_args : '',
            analyzeduration_us: Math.max(10000, Math.min(30_000_000, Number(pb.backends?.ffmpeg?.analyzeduration_us) || 500000)),
            probesize: Math.max(10000, Math.min(50_000_000, Number(pb.backends?.ffmpeg?.probesize) || 500000)),
            hls_time: Math.max(1, Math.min(30, Number(pb.backends?.ffmpeg?.hls_time) || 2)),
            hls_list_size: Math.max(2, Math.min(30, Number(pb.backends?.ffmpeg?.hls_list_size) || 5)),
          },
          vlc: {
            bin: (pb.backends?.vlc?.bin || 'vlc').trim() || 'vlc',
            buffer_kb: Math.max(64, Math.min(65536, Number(pb.backends?.vlc?.buffer_kb) || 1024)),
            hls_time: Math.max(1, Math.min(30, Number(pb.backends?.vlc?.hls_time) || 2)),
            hls_list_size: Math.max(2, Math.min(30, Number(pb.backends?.vlc?.hls_list_size) || 5)),
          },
          gstreamer: {
            bin: (pb.backends?.gstreamer?.bin || 'gst-launch-1.0').trim() || 'gst-launch-1.0',
            buffer_kb: Math.max(64, Math.min(65536, Number(pb.backends?.gstreamer?.buffer_kb) || 1024)),
            hls_time: Math.max(1, Math.min(30, Number(pb.backends?.gstreamer?.hls_time) || 2)),
            hls_list_size: Math.max(2, Math.min(30, Number(pb.backends?.gstreamer?.hls_list_size) || 5)),
          },
          tsduck: {
            bin: (pb.backends?.tsduck?.bin || 'tsp').trim() || 'tsp',
            buffer_kb: Math.max(64, Math.min(65536, Number(pb.backends?.tsduck?.buffer_kb) || 1024)),
            hls_time: Math.max(1, Math.min(30, Number(pb.backends?.tsduck?.hls_time) || 2)),
            hls_list_size: Math.max(2, Math.min(30, Number(pb.backends?.tsduck?.hls_list_size) || 5)),
          },
          astra: {
            relay_url: (typeof pb.backends?.astra?.relay_url === 'string' && pb.backends.astra.relay_url.trim())
              ? pb.backends.astra.relay_url.trim()
              : 'http://localhost:8000',
          },
          webrtc: pb.backends?.webrtc ?? {},
        },
      },
    },
  }
}

async function load() {
  loading.value = true
  saveError.value = ''
  try {
    settings.value = await api.settingsGet()
    form.value = formFromModules(settings.value.modules)
  } catch (e) {
    saveError.value = e?.message || 'Не удалось загрузить настройки'
  } finally {
    loading.value = false
  }
}

async function save(silent = false) {
  if (!silent) {
    saving.value = true
    saveOk.value = false
    saveError.value = ''
  }
  try {
    const payload = { modules: formToModules() }
    const updated = await api.settingsPut(payload)
    settings.value = updated
    form.value = formFromModules(updated.modules)
    if (!silent) {
      saveOk.value = true
      setTimeout(() => { saveOk.value = false }, 3000)
    }
  } catch (e) {
    saveError.value = e?.message || 'Не удалось сохранить'
  } finally {
    if (!silent) saving.value = false
  }
}

onMounted(load)
</script>
