<template>
  <div class="p-8 max-w-7xl mx-auto">
    <header class="mb-8">
      <div class="flex flex-wrap items-start justify-between gap-6">
        <div>
          <h1 class="text-2xl font-semibold text-white">Каналы</h1>
          <p class="text-slate-400 mt-1">Все каналы по инстансам Astra</p>
        </div>
        <div class="rounded-xl border border-surface-600 bg-surface-800/80 p-2 flex flex-wrap items-center gap-2">
          <div class="flex items-center gap-2 px-3 py-2 rounded-lg">
            <span class="text-xs text-slate-500 font-medium">Список каналов</span>
            <span class="text-sm font-semibold text-white tabular-nums">{{ channels.length }}</span>
          </div>
          <span class="w-px h-8 bg-surface-600 flex-shrink-0" aria-hidden="true" />
          <div class="flex items-center rounded-lg p-0.5 bg-surface-700/50" role="group" aria-label="Вид">
            <button
              type="button"
              :class="viewMode === 'table' ? 'bg-surface-600 text-white shadow-sm' : 'text-slate-400 hover:text-white hover:bg-surface-700'"
              class="rounded-md px-4 py-2 text-sm font-medium transition-colors"
              @click="viewMode = 'table'"
            >
              Таблица
            </button>
            <button
              type="button"
              :class="viewMode === 'cards' ? 'bg-surface-600 text-white shadow-sm' : 'text-slate-400 hover:text-white hover:bg-surface-700'"
              class="rounded-md px-4 py-2 text-sm font-medium transition-colors"
              @click="viewMode = 'cards'"
            >
              Карточки
            </button>
          </div>
          <span class="w-px h-8 bg-surface-600 flex-shrink-0" aria-hidden="true" />
          <label class="flex items-center gap-2 px-3 py-2 rounded-lg cursor-pointer hover:bg-surface-700/50 transition-colors">
            <input type="checkbox" v-model="groupByInstance" class="rounded border-surface-600 bg-surface-800 text-accent" />
            <span class="text-sm text-slate-400">Группировать по экземпляру</span>
          </label>
          <span class="w-px h-8 bg-surface-600 flex-shrink-0" aria-hidden="true" />
          <button
            type="button"
            @click="load"
            :disabled="loading"
            class="rounded-lg px-4 py-2 text-sm font-medium bg-surface-700 text-slate-300 hover:bg-surface-600 hover:text-white disabled:opacity-50 disabled:hover:bg-surface-700 disabled:hover:text-slate-300 transition-colors"
          >
            {{ loading ? 'Загрузка…' : 'Обновить' }}
          </button>
        </div>
      </div>
    </header>

    <div v-if="loading && !channels.length" class="flex justify-center py-20">
      <div class="w-10 h-10 border-2 border-accent/40 border-t-accent rounded-full animate-spin" />
    </div>

    <div v-else-if="!channels.length" class="rounded-2xl bg-surface-800/60 border border-surface-700 p-12 text-center text-slate-400">
      Нет каналов или инстансы недоступны.
    </div>

    <!-- Таблица: Имя → Превью → Output → Действия -->
    <div v-else-if="viewMode === 'table'" class="rounded-xl border border-surface-700 bg-surface-800/60 overflow-hidden">
      <table class="w-full text-sm">
        <thead>
          <tr class="border-b border-surface-700 text-left text-slate-400">
            <th class="px-4 py-3.5 font-medium cursor-pointer select-none hover:text-white" @click="cycleSort">
              Имя <span v-if="sortByName" class="ml-1 text-accent">{{ sortByName === 'asc' ? '↑' : '↓' }}</span>
            </th>
            <th class="px-3 py-3.5 font-medium w-28">Превью</th>
            <th class="px-4 py-3.5 font-medium">Output</th>
            <th class="px-4 py-3.5 font-medium w-40">Действия</th>
          </tr>
        </thead>
        <template v-if="groupByInstance">
          <template v-for="(group, gi) in groupedChannels" :key="group.port">
            <tr :class="gi > 0 ? 'border-t-2 border-surface-600' : ''">
              <td colspan="4" class="px-4 py-3 bg-surface-750/80 border-b border-surface-600">
                <div class="flex items-center gap-3">
                  <span class="w-1 h-6 rounded-full bg-accent flex-shrink-0" aria-hidden="true" />
                  <span class="font-mono font-semibold text-accent">:{{ group.port }}</span>
                  <span class="text-slate-500 text-sm">Экземпляр</span>
                  <span class="text-slate-500 text-sm font-normal tabular-nums">{{ group.channels.length }} {{ group.channels.length === 1 ? 'канал' : group.channels.length < 5 ? 'канала' : 'каналов' }}</span>
                </div>
              </td>
            </tr>
            <tr
              v-for="ch in group.channels"
              :key="ch.instance_id + ':' + ch.name"
              class="border-t border-surface-700/50 hover:bg-surface-750/30 transition-colors"
            >
              <td class="px-4 py-3 align-middle">
                <span
                  class="block truncate max-w-[200px] text-white"
                  :title="(ch.display_name || ch.name) + (ch.display_name ? ` (API: ${ch.name})` : '')"
                >
                  {{ ch.display_name || ch.name }}
                </span>
              </td>
              <td class="px-3 py-3 align-middle">
                <div class="relative inline-block w-24 h-14 rounded-lg overflow-hidden bg-surface-700 border border-surface-600">
                <img
                  v-if="previewUrl(ch)"
                  :src="previewUrl(ch)"
                  alt=""
                  class="w-full h-full object-cover"
                  loading="lazy"
                  @error="($event.target).src = previewPlaceholder"
                />
                <span v-if="previewGeneratedAt(ch)" class="absolute bottom-0 right-0 bg-black/75 text-white text-[10px] px-1 rounded-tl" :title="previewGeneratedAt(ch)">{{ previewGeneratedAt(ch) }}</span>
                <span v-else-if="!previewUrl(ch)" class="absolute inset-0 flex items-center justify-center text-slate-500 text-xs">—</span>
              </div>
              </td>
              <td class="px-4 py-3 align-middle">
                <template v-if="(ch.output || []).length">
                  <button
                    v-for="(url, i) in (ch.output || [])"
                    :key="i"
                    type="button"
                    :title="url"
                    class="block text-accent hover:underline truncate max-w-md text-left py-0.5"
                    @click="openPlayer(ch)"
                  >
                    {{ url }}
                  </button>
                </template>
                <span v-else class="text-slate-500">—</span>
              </td>
              <td class="px-4 py-3 align-middle">
                <div class="flex gap-1.5">
                  <button type="button" title="Перезапуск" class="rounded-lg bg-surface-700 text-slate-300 p-2 hover:bg-surface-600 disabled:opacity-50" :disabled="actioning" @click="restart(ch)">
                    <svg xmlns="http://www.w3.org/2000/svg" class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" /></svg>
                  </button>
                  <button type="button" title="Отключить" class="rounded-lg bg-danger/20 text-danger border border-danger/40 p-2 hover:bg-danger/30 disabled:opacity-50" :disabled="actioning" @click="kill(ch)">
                    <svg xmlns="http://www.w3.org/2000/svg" class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M18.36 6.64a9 9 0 11-12.73 0M12 2v10" /></svg>
                  </button>
                  <button type="button" title="Switch Input" class="rounded-lg bg-surface-700 text-slate-300 p-2 hover:bg-surface-600 disabled:opacity-50" :disabled="actioning" @click="switchInput(ch)">
                    <svg xmlns="http://www.w3.org/2000/svg" class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M8 7h12m0 0l-4-4m4 4l-4 4m0 6H4m0 0l4 4m-4-4l4-4" /></svg>
                  </button>
                </div>
              </td>
            </tr>
          </template>
        </template>
        <template v-else-if="useTableVirtualList">
          <!-- Виртуальный список: рендер только видимых строк при большом числе каналов -->
          <div v-bind="tableContainerProps" class="overflow-auto border-t border-surface-700 bg-surface-800/40" style="max-height: min(70vh, 600px)">
            <div v-bind="tableWrapperProps">
              <div
                v-for="item in tableVirtualList"
                :key="channelKey(item.data)"
                class="grid w-full grid-cols-[minmax(0,1fr)_7rem_minmax(0,1fr)_10rem] gap-0 border-t border-surface-700/50 hover:bg-surface-750/30 transition-colors items-center text-sm"
                :style="{ height: TABLE_ROW_HEIGHT + 'px', minHeight: TABLE_ROW_HEIGHT + 'px' }"
              >
                <div class="px-4 flex items-center min-w-0">
                  <span
                    class="block truncate max-w-[200px] text-white"
                    :title="(item.data.display_name || item.data.name) + (item.data.display_name ? ` (API: ${item.data.name})` : '')"
                  >
                    {{ item.data.display_name || item.data.name }}
                  </span>
                </div>
                <div class="px-3 flex items-center">
                  <div class="relative inline-block w-24 h-14 rounded-lg overflow-hidden bg-surface-700 border border-surface-600 flex-shrink-0">
                    <img
                      v-if="previewUrl(item.data)"
                      :src="previewUrl(item.data)"
                      alt=""
                      class="w-full h-full object-cover"
                      loading="lazy"
                      @error="($event.target).src = previewPlaceholder"
                    />
                    <span v-if="previewGeneratedAt(item.data)" class="absolute bottom-0 right-0 bg-black/75 text-white text-[10px] px-1 rounded-tl" :title="previewGeneratedAt(item.data)">{{ previewGeneratedAt(item.data) }}</span>
                    <span v-else-if="!previewUrl(item.data)" class="absolute inset-0 flex items-center justify-center text-slate-500 text-xs">—</span>
                  </div>
                </div>
                <div class="px-4 flex items-center min-w-0">
                  <template v-if="(item.data.output || []).length">
                    <button
                      v-for="(url, i) in (item.data.output || [])"
                      :key="i"
                      type="button"
                      :title="url"
                      class="block text-accent hover:underline truncate max-w-md text-left py-0.5"
                      @click="openPlayer(item.data)"
                    >
                      {{ url }}
                    </button>
                  </template>
                  <span v-else class="text-slate-500">—</span>
                </div>
                <div class="px-4 flex items-center">
                  <div class="flex gap-1.5">
                    <button type="button" title="Перезапуск" class="rounded-lg bg-surface-700 text-slate-300 p-2 hover:bg-surface-600 disabled:opacity-50" :disabled="actioning" @click="restart(item.data)">
                      <svg xmlns="http://www.w3.org/2000/svg" class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" /></svg>
                    </button>
                    <button type="button" title="Отключить" class="rounded-lg bg-danger/20 text-danger border border-danger/40 p-2 hover:bg-danger/30 disabled:opacity-50" :disabled="actioning" @click="kill(item.data)">
                      <svg xmlns="http://www.w3.org/2000/svg" class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M18.36 6.64a9 9 0 11-12.73 0M12 2v10" /></svg>
                    </button>
                    <button type="button" title="Switch Input" class="rounded-lg bg-surface-700 text-slate-300 p-2 hover:bg-surface-600 disabled:opacity-50" :disabled="actioning" @click="switchInput(item.data)">
                      <svg xmlns="http://www.w3.org/2000/svg" class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M8 7h12m0 0l-4-4m4 4l-4 4m0 6H4m0 0l4 4m-4-4l4-4" /></svg>
                    </button>
                    <button type="button" title="Анализ потока (TSDuck)" class="rounded-lg bg-surface-700 text-slate-300 p-2 hover:bg-surface-600 disabled:opacity-50" :disabled="actioning || analyzing" @click="openAnalysis(item.data)">
                      <svg xmlns="http://www.w3.org/2000/svg" class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" /></svg>
                    </button>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </template>
        <tbody v-else>
          <tr v-for="ch in sortedChannels" :key="ch.instance_id + ':' + ch.name" class="border-t border-surface-700/50 hover:bg-surface-750/30 transition-colors">
            <td class="px-4 py-3 align-middle">
              <span
                class="block truncate max-w-[200px] text-white"
                :title="(ch.display_name || ch.name) + (ch.display_name ? ` (API: ${ch.name})` : '')"
              >
                {{ ch.display_name || ch.name }}
              </span>
            </td>
            <td class="px-3 py-3 align-middle">
              <div class="relative inline-block w-24 h-14 rounded-lg overflow-hidden bg-surface-700 border border-surface-600">
                <img
                  v-if="previewUrl(ch)"
                  :src="previewUrl(ch)"
                  alt=""
                  class="w-full h-full object-cover"
                  loading="lazy"
                  @error="($event.target).src = previewPlaceholder"
                />
                <span v-if="previewGeneratedAt(ch)" class="absolute bottom-0 right-0 bg-black/75 text-white text-[10px] px-1 rounded-tl" :title="previewGeneratedAt(ch)">{{ previewGeneratedAt(ch) }}</span>
                <span v-else-if="!previewUrl(ch)" class="absolute inset-0 flex items-center justify-center text-slate-500 text-xs">—</span>
              </div>
            </td>
            <td class="px-4 py-3 align-middle">
              <template v-if="(ch.output || []).length">
                <button
                  v-for="(url, i) in (ch.output || [])"
                  :key="i"
                  type="button"
                  :title="url"
                  class="block text-accent hover:underline truncate max-w-md text-left py-0.5"
                  @click="openPlayer(ch)"
                >
                  {{ url }}
                </button>
              </template>
              <span v-else class="text-slate-500">—</span>
            </td>
            <td class="px-4 py-3 align-middle">
              <div class="flex gap-1.5">
                <button type="button" title="Перезапуск" class="rounded-lg bg-surface-700 text-slate-300 p-2 hover:bg-surface-600 disabled:opacity-50" :disabled="actioning" @click="restart(ch)">
                  <svg xmlns="http://www.w3.org/2000/svg" class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" /></svg>
                </button>
                <button type="button" title="Отключить" class="rounded-lg bg-danger/20 text-danger border border-danger/40 p-2 hover:bg-danger/30 disabled:opacity-50" :disabled="actioning" @click="kill(ch)">
                  <svg xmlns="http://www.w3.org/2000/svg" class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M18.36 6.64a9 9 0 11-12.73 0M12 2v10" /></svg>
                </button>
                <button type="button" title="Switch Input" class="rounded-lg bg-surface-700 text-slate-300 p-2 hover:bg-surface-600 disabled:opacity-50" :disabled="actioning" @click="switchInput(ch)">
                  <svg xmlns="http://www.w3.org/2000/svg" class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M8 7h12m0 0l-4-4m4 4l-4 4m0 6H4m0 0l4 4m-4-4l4-4" /></svg>
                </button>
                <button type="button" title="Анализ потока (TSDuck)" class="rounded-lg bg-surface-700 text-slate-300 p-2 hover:bg-surface-600 disabled:opacity-50" :disabled="actioning || analyzing" @click="openAnalysis(ch)">
                  <svg xmlns="http://www.w3.org/2000/svg" class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" /></svg>
                </button>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- Карточки: при группировке — секции по экземпляру, иначе — плоская сетка -->
    <div v-else class="space-y-6">
      <template v-if="groupByInstance">
        <section v-for="group in groupedChannels" :key="group.port" class="rounded-xl border border-surface-700 bg-surface-800/60 overflow-hidden">
          <div class="px-4 py-3 flex items-center gap-3 border-b border-surface-700 bg-surface-750/80">
            <span class="w-1 h-5 rounded-full bg-accent flex-shrink-0" />
            <span class="font-mono font-semibold text-accent">:{{ group.port }}</span>
            <span class="text-slate-500 text-sm">Экземпляр · {{ group.channels.length }} {{ group.channels.length === 1 ? 'канал' : group.channels.length < 5 ? 'канала' : 'каналов' }}</span>
          </div>
          <div class="p-4 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            <article
              v-for="ch in group.channels"
              :key="ch.instance_id + ':' + ch.name"
              class="rounded-xl border border-surface-700 bg-surface-750/50 overflow-hidden transition-all hover:border-surface-600"
            >
              <p class="p-3 pb-0 font-medium text-white truncate" :title="ch.display_name ? `API: ${ch.name}` : ''">{{ ch.display_name || ch.name }}</p>
              <div class="p-3">
                <div class="relative w-full aspect-video rounded-xl bg-surface-800 border border-surface-600 overflow-hidden ring-1 ring-black/20 shadow-inner">
                  <template v-if="inlinePlayback && inlinePlayback.channelKey === channelKey(ch)">
                    <video
                      :ref="(el) => setInlineVideoRef(channelKey(ch), el)"
                      class="absolute inset-0 w-full h-full object-cover"
                      muted
                      playsinline
                      autoplay
                    />
                    <button
                      type="button"
                      class="absolute bottom-2 right-2 flex items-center gap-1.5 rounded-lg bg-black/60 hover:bg-black/75 px-2.5 py-1.5 text-white text-xs font-medium transition-colors shadow-lg"
                      title="Открыть в плеере"
                      @click.stop="openPlayerFromInline(ch)"
                    >
                      <svg xmlns="http://www.w3.org/2000/svg" class="w-4 h-4" fill="currentColor" viewBox="0 0 24 24"><path d="M8 5v14l11-7z"/></svg>
                      Открыть в плеере
                    </button>
                    <p v-if="inlinePlaybackError" class="absolute bottom-2 left-2 right-14 rounded bg-red-900/80 text-red-200 text-xs px-2 py-1 truncate">{{ inlinePlaybackError }}</p>
                  </template>
                  <template v-else>
                    <img
                      v-if="previewUrl(ch)"
                      :src="previewUrl(ch)"
                      alt=""
                      class="w-full h-full object-cover"
                      loading="lazy"
                      @error="($event.target).src = previewPlaceholder"
                    />
                    <span v-if="previewGeneratedAt(ch)" class="absolute bottom-0 right-0 bg-black/75 text-white text-[10px] px-1.5 py-0.5 rounded-tl" :title="previewGeneratedAt(ch)">{{ previewGeneratedAt(ch) }}</span>
                    <span v-else-if="!previewUrl(ch)" class="absolute inset-0 flex items-center justify-center text-slate-500 text-sm">—</span>
                  </template>
                </div>
              </div>
              <div class="px-3 pb-2">
                <template v-if="(ch.output || []).length">
                  <button
                    v-for="(url, i) in (ch.output || [])"
                    :key="i"
                    type="button"
                    :title="url"
                    class="text-accent hover:underline text-xs truncate block text-left w-full"
                    @click="startInlineOrOpenPlayer(ch)"
                  >
                    {{ url }}
                  </button>
                </template>
                <p v-else class="text-slate-500 text-xs">—</p>
              </div>
              <div class="px-3 pb-3 flex gap-2">
                <button type="button" title="Перезапуск" class="rounded-lg bg-surface-700 text-slate-300 p-2 hover:bg-surface-600 disabled:opacity-50" :disabled="actioning" @click="restart(ch)">
                  <svg xmlns="http://www.w3.org/2000/svg" class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" /></svg>
                </button>
                <button type="button" title="Отключить" class="rounded-lg bg-danger/20 text-danger border border-danger/40 p-2 hover:bg-danger/30 disabled:opacity-50" :disabled="actioning" @click="kill(ch)">
                  <svg xmlns="http://www.w3.org/2000/svg" class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M18.36 6.64a9 9 0 11-12.73 0M12 2v10" /></svg>
                </button>
                <button type="button" title="Анализ потока (TSDuck)" class="rounded-lg bg-surface-700 text-slate-300 p-2 hover:bg-surface-600 disabled:opacity-50" :disabled="actioning || analyzing" @click="openAnalysis(ch)">
                  <svg xmlns="http://www.w3.org/2000/svg" class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" /></svg>
                </button>
              </div>
            </article>
          </div>
        </section>
      </template>
      <div v-else class="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        <article
          v-for="ch in sortedChannels"
          :key="ch.instance_id + ':' + ch.name"
          class="rounded-xl border border-surface-700 bg-surface-800/60 overflow-hidden transition-all hover:border-surface-600"
        >
          <p class="p-3 pb-0 font-medium text-white truncate" :title="ch.display_name ? `API: ${ch.name}` : ''">{{ ch.display_name || ch.name }}</p>
          <div class="p-3">
            <div class="relative w-full aspect-video rounded-xl bg-surface-800 border border-surface-600 overflow-hidden ring-1 ring-black/20 shadow-inner">
              <template v-if="inlinePlayback && inlinePlayback.channelKey === channelKey(ch)">
                <video
                  :ref="(el) => setInlineVideoRef(channelKey(ch), el)"
                  class="absolute inset-0 w-full h-full object-cover"
                  muted
                  playsinline
                  autoplay
                />
                <button
                  type="button"
                  class="absolute bottom-2 right-2 flex items-center gap-1.5 rounded-lg bg-black/60 hover:bg-black/75 px-2.5 py-1.5 text-white text-xs font-medium transition-colors shadow-lg"
                  title="Открыть в плеере"
                  @click.stop="openPlayerFromInline(ch)"
                >
                  <svg xmlns="http://www.w3.org/2000/svg" class="w-4 h-4" fill="currentColor" viewBox="0 0 24 24"><path d="M8 5v14l11-7z"/></svg>
                  Открыть в плеере
                </button>
                <p v-if="inlinePlaybackError" class="absolute bottom-2 left-2 right-14 rounded bg-red-900/80 text-red-200 text-xs px-2 py-1 truncate">{{ inlinePlaybackError }}</p>
              </template>
              <template v-else>
                <img
                  v-if="previewUrl(ch)"
                  :src="previewUrl(ch)"
                  alt=""
                  class="w-full h-full object-cover"
                  loading="lazy"
                  @error="($event.target).src = previewPlaceholder"
                />
                <span v-if="previewGeneratedAt(ch)" class="absolute bottom-0 right-0 bg-black/75 text-white text-[10px] px-1.5 py-0.5 rounded-tl" :title="previewGeneratedAt(ch)">{{ previewGeneratedAt(ch) }}</span>
                <span v-else-if="!previewUrl(ch)" class="absolute inset-0 flex items-center justify-center text-slate-500 text-sm">—</span>
              </template>
            </div>
          </div>
          <div class="px-3 pb-2">
            <template v-if="(ch.output || []).length">
              <button
                v-for="(url, i) in (ch.output || [])"
                :key="i"
                type="button"
                :title="url"
                class="text-accent hover:underline text-xs truncate block text-left w-full"
                @click="startInlineOrOpenPlayer(ch)"
              >
                {{ url }}
              </button>
            </template>
            <p v-else class="text-slate-500 text-xs">—</p>
          </div>
          <div class="px-3 pb-3 flex gap-2">
            <button type="button" title="Перезапуск" class="rounded-lg bg-surface-700 text-slate-300 p-2 hover:bg-surface-600 disabled:opacity-50" :disabled="actioning" @click="restart(ch)">
              <svg xmlns="http://www.w3.org/2000/svg" class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" /></svg>
            </button>
            <button type="button" title="Отключить" class="rounded-lg bg-danger/20 text-danger border border-danger/40 p-2 hover:bg-danger/30 disabled:opacity-50" :disabled="actioning" @click="kill(ch)">
              <svg xmlns="http://www.w3.org/2000/svg" class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M18.36 6.64a9 9 0 11-12.73 0M12 2v10" /></svg>
            </button>
            <button type="button" title="Анализ потока (TSDuck)" class="rounded-lg bg-surface-700 text-slate-300 p-2 hover:bg-surface-600 disabled:opacity-50" :disabled="actioning || analyzing" @click="openAnalysis(ch)">
              <svg xmlns="http://www.w3.org/2000/svg" class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" /></svg>
            </button>
          </div>
        </article>
      </div>
    </div>

    <!-- Модальное окно проигрывателя -->
    <div v-if="playerModal" class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70" @click.self="closePlayer">
      <div class="rounded-2xl bg-surface-800 border border-surface-600 shadow-xl w-full max-w-4xl overflow-hidden" @click.stop>
        <div class="p-4 flex items-center justify-between border-b border-surface-700">
          <h3 class="text-lg font-medium text-white truncate">{{ playerModal.channelName }}</h3>
          <div class="flex items-center gap-2">
            <button type="button" class="rounded-lg bg-surface-700 text-slate-300 p-2 hover:bg-surface-600" title="Полноэкранный режим" @click="togglePlayerFullscreen">
              <svg xmlns="http://www.w3.org/2000/svg" class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M4 8V4m0 0h4M4 4l5 5m11-1V4m0 0h-4m4 0l-5 5M4 16v4m0 0h4m-4 0l5-5m11 5l-5-5m5 5v-4m0 4h-4" /></svg>
            </button>
            <button type="button" class="rounded-lg bg-surface-700 text-slate-300 p-2 hover:bg-surface-600" @click="closePlayer">
              <svg xmlns="http://www.w3.org/2000/svg" class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" /></svg>
            </button>
          </div>
        </div>
        <div class="aspect-video bg-black flex items-center justify-center relative">
          <video
            ref="playerVideoEl"
            class="w-full h-full"
            controls
            muted
            playsinline
            title="Двойной клик — полноэкранный режим"
            @dblclick="togglePlayerFullscreen"
          />
          <p v-if="playerError" class="text-danger text-sm p-4 absolute">{{ playerError }}</p>
          <p v-else-if="playerModal && !playerModal.ready" class="text-slate-400 absolute">Загрузка…</p>
        </div>
      </div>
    </div>

    <!-- Модальное окно анализа потока (TSDuck) -->
    <div v-if="analysisModal" class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70" @click.self="closeAnalysis">
      <div class="rounded-2xl bg-surface-800 border border-surface-600 shadow-xl w-full max-w-2xl max-h-[85vh] overflow-hidden flex flex-col" @click.stop>
        <div class="p-4 flex items-center justify-between border-b border-surface-700 flex-shrink-0">
          <h3 class="text-lg font-medium text-white truncate">Анализ: {{ analysisModal.channelName }}</h3>
          <button type="button" class="rounded-lg bg-surface-700 text-slate-300 p-2 hover:bg-surface-600" @click="closeAnalysis">
            <svg xmlns="http://www.w3.org/2000/svg" class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" /></svg>
          </button>
        </div>
        <p v-if="analysisModal.url" class="px-4 py-1 text-xs text-slate-500 truncate border-b border-surface-700" :title="analysisModal.url">{{ analysisModal.url }}</p>
        <div class="p-4 overflow-auto flex-1 min-h-0">
          <pre class="text-sm text-slate-300 whitespace-pre-wrap font-mono break-words" :class="analysisModal.ok ? '' : 'text-red-300'">{{ analysisModal.output }}</pre>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount, nextTick } from 'vue'
import { useVirtualList } from '@vueuse/core'
import Hls from 'hls.js'
import mpegts from 'mpegts.js'
import api from '../api'

/** Порог: при числе каналов >= этого значения таблица (без группировки) рендерится через виртуальный список */
const VIRTUAL_LIST_THRESHOLD = 40
/** Высота одной строки таблицы (px) — должна совпадать с реальной высотой строки */
const TABLE_ROW_HEIGHT = 72

const loading = ref(true)
const actioning = ref(false)
const channels = ref([])
const sortByName = ref('asc')
const groupByInstance = ref(false)
const viewMode = ref('table')
const tabOpenTime = ref(Date.now())

const playerModal = ref(null)
const playerVideoEl = ref(null)
const playerError = ref('')
let playerHls = null
let playerMpegts = null

const inlinePlayback = ref(null)
const inlinePlaybackError = ref('')
const inlineVideoRefs = ref({})
let inlineHls = null
let inlineMpegts = null
/** Одна повторная попытка при фатальной ошибке HLS */
let inlineHlsRetryUsed = false
let playerHlsRetryUsed = false

const analysisModal = ref(null)
const analyzing = ref(false)

/** После окончания цикла обновления превью — подставляем &t= чтобы браузер подхватил новые картинки */
const previewRefreshVersion = ref(0)
let previewRefreshEventSource = null

function channelKey(ch) {
  return `${ch.instance_id}:${ch.name}`
}

function setInlineVideoRef(key, el) {
  const refs = inlineVideoRefs.value
  const node = el && (Array.isArray(el) ? el[0] : el)
  if (node) refs[key] = node
  else delete refs[key]
}

function clearInlineVideo() {
  if (inlineHls) {
    inlineHls.destroy()
    inlineHls = null
  }
  if (inlineMpegts) {
    inlineMpegts.destroy()
    inlineMpegts = null
  }
  inlinePlayback.value = null
}

function stopInlinePlayback() {
  if (inlineHls) {
    inlineHls.destroy()
    inlineHls = null
  }
  if (inlineMpegts) {
    inlineMpegts.destroy()
    inlineMpegts = null
  }
  if (inlinePlayback.value?.sessionId) {
    api.streamPlaybackStop(inlinePlayback.value.sessionId).catch(() => {})
  }
  inlinePlayback.value = null
}

const hlsConfig = {
  maxBufferLength: 12,
  maxMaxBufferLength: 30,
  // без startLevel: -1 — стабильнее при нестабильном плейлисте
}

function attachInlinePlayer(fullUrl, playbackUrl, key, useNativeVideo = false, useMpegtsJs = false) {
  const video = inlineVideoRefs.value[key]
  if (!video) return
  if (inlineHls) {
    inlineHls.destroy()
    inlineHls = null
  }
  if (inlineMpegts) {
    inlineMpegts.destroy()
    inlineMpegts = null
  }
  video.src = ''
  inlinePlaybackError.value = ''
  if (useMpegtsJs) {
    if (mpegts.isSupported()) {
      inlineMpegts = mpegts.createPlayer(
        { type: 'mse', isLive: true, url: fullUrl },
        { isLive: true }
      )
      inlineMpegts.attachMediaElement(video)
      inlineMpegts.on(mpegts.Events.ERROR, (_, data) => {
        const msg = data?.message || data?.reason || 'Ошибка потока'
        inlinePlaybackError.value = typeof msg === 'string' ? msg.slice(0, 80) : 'Ошибка загрузки потока'
      })
      inlineMpegts.load()
      inlineMpegts.play()
    } else {
      inlinePlaybackError.value = 'Воспроизведение MPEG-TS не поддерживается в этом браузере'
    }
  } else if (!useNativeVideo && (playbackUrl.includes('.m3u8') || playbackUrl.includes('/streams/') || playbackUrl.includes('/streams/proxy/'))) {
    if (Hls.isSupported()) {
      inlineHls = new Hls(hlsConfig)
      inlineHls.loadSource(fullUrl)
      inlineHls.attachMedia(video)
      inlineHls.on(Hls.Events.ERROR, (_, data) => {
        if (!data.fatal) return
        if (!inlineHlsRetryUsed) {
          inlineHlsRetryUsed = true
          inlineHls.destroy()
          inlineHls = null
          setTimeout(() => attachInlinePlayer(fullUrl, playbackUrl, key, useNativeVideo, useMpegtsJs), 800)
          return
        }
        inlinePlaybackError.value = 'Ошибка загрузки потока'
      })
    } else if (video.canPlayType('application/vnd.apple.mpegurl')) {
      video.src = fullUrl
    }
  } else {
    video.src = fullUrl
  }
  video.play().catch(() => {})
}

async function startInlineOrOpenPlayer(ch) {
  const key = channelKey(ch)
  if (inlinePlayback.value?.channelKey === key) {
    openPlayerFromInline(ch)
    return
  }
  stopInlinePlayback()
  inlinePlaybackError.value = ''
  inlineHlsRetryUsed = false
  try {
    const data = await api.streamPlaybackStart({ instance_id: ch.instance_id, channel_name: ch.name })
    const playbackUrl = data?.playback_url
    if (!playbackUrl) {
      inlinePlaybackError.value = 'Нет URL воспроизведения'
      return
    }
    const sessionId = data?.session_id ?? null
    const useNativeVideo = !!data?.use_native_video
    const useMpegtsJs = !!data?.use_mpegts_js
    const fullUrl = playbackUrl.startsWith('http') ? playbackUrl : `${window.location.origin}${playbackUrl.startsWith('/') ? '' : '/'}${playbackUrl}`
    inlinePlayback.value = { channelKey: key, fullUrl, playbackUrl, sessionId, channelName: ch.display_name || ch.name, useNativeVideo, useMpegtsJs }
    await nextTick()
    attachInlinePlayer(fullUrl, playbackUrl, key, useNativeVideo, useMpegtsJs)
  } catch (e) {
    let msg = e?.message || String(e)
    try {
      const d = typeof msg === 'string' && msg.startsWith('{') ? JSON.parse(msg) : null
      if (d && d.detail) msg = typeof d.detail === 'string' ? d.detail : String(d.detail)
    } catch (_) {}
    if (!msg || msg.length > 120) msg = msg ? msg.slice(0, 117) + '…' : 'Не удалось запустить воспроизведение'
    inlinePlaybackError.value = msg
  }
}

function openPlayerFromInline(ch) {
  const cur = inlinePlayback.value
  if (!cur || cur.channelKey !== channelKey(ch)) return
  clearInlineVideo()
  playerError.value = ''
  playerHlsRetryUsed = false
  playerModal.value = { channelName: cur.channelName, playbackUrl: cur.fullUrl, sessionId: cur.sessionId, ready: true, useNativeVideo: cur.useNativeVideo, useMpegtsJs: cur.useMpegtsJs }
  nextTick().then(() => attachPlayer(cur.fullUrl, cur.playbackUrl, cur.useNativeVideo, cur.useMpegtsJs))
}

async function openAnalysis(ch) {
  if (analyzing.value) return
  analyzing.value = true
  analysisModal.value = null
  try {
    const data = await api.channelAnalyze(ch.instance_id, ch.name)
    analysisModal.value = {
      channelName: ch.display_name || ch.name,
      output: data.output ?? '(нет вывода)',
      ok: data.ok === true,
      url: data.url ?? '',
    }
  } catch (e) {
    analysisModal.value = {
      channelName: ch.display_name || ch.name,
      output: e?.message ?? 'Ошибка запроса анализа',
      ok: false,
      url: '',
    }
  } finally {
    analyzing.value = false
  }
}

function closeAnalysis() {
  analysisModal.value = null
}

function hasPreview(ch) {
  return (ch.output || []).length > 0
}

/** Плейсхолдер при 404/502 (превью ещё нет в кэше или ошибка) */
const previewPlaceholder = "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='96' height='56'%3E%3Crect fill='%23334155' width='96' height='56'/%3E%3Ctext x='50%25' y='50%25' dominant-baseline='middle' text-anchor='middle' fill='%2394a3b8' font-size='10'%3E—%3C/text%3E%3C/svg%3E"

/** URL превью: из кэша бэкенда; после окончания цикла обновления добавляем &t= чтобы подхватить новые картинки */
function previewUrl(ch) {
  if (!hasPreview(ch)) return ''
  const base = api.channelPreviewUrl(ch.instance_id, ch.name)
  return previewRefreshVersion.value ? `${base}&t=${previewRefreshVersion.value}` : base
}

/** Дата в подписи к превью (опционально, по заголовку при загрузке) — не используем object URL */
function previewGeneratedAt(_ch) {
  return null
}

function cycleSort() {
  if (sortByName.value === '') sortByName.value = 'asc'
  else if (sortByName.value === 'asc') sortByName.value = 'desc'
  else sortByName.value = ''
}

const sortedChannels = computed(() => {
  const list = [...channels.value]
  const key = (c) => (c.display_name || c.name || '')
  if (sortByName.value === 'asc') list.sort((a, b) => key(a).localeCompare(key(b)))
  else if (sortByName.value === 'desc') list.sort((a, b) => key(b).localeCompare(key(a)))
  return list
})

const groupedChannels = computed(() => {
  const byPort = new Map()
  for (const ch of sortedChannels.value) {
    const port = ch.instance_port
    if (!byPort.has(port)) byPort.set(port, { port, channels: [] })
    byPort.get(port).channels.push(ch)
  }
  return Array.from(byPort.values())
})

/** Виртуальный список для таблицы (плоский список без группировки); используется в шаблоне при большом числе каналов */
const { list: tableVirtualList, containerProps: tableContainerProps, wrapperProps: tableWrapperProps } = useVirtualList(
  sortedChannels,
  { itemHeight: TABLE_ROW_HEIGHT, overscan: 10 }
)

const useTableVirtualList = computed(() => viewMode.value === 'table' && !groupByInstance.value && sortedChannels.value.length >= VIRTUAL_LIST_THRESHOLD)

async function load() {
  loading.value = true
  try {
    const res = await api.aggregateChannels()
    channels.value = res.channels || []
    tabOpenTime.value = Date.now()
    try {
      const refresh = await api.channelsPreviewRefreshStart()
      if (refresh?.started) startPreviewRefreshSSE()
    } catch (_) {}
  } catch {
    channels.value = []
  } finally {
    loading.value = false
  }
}

function startPreviewRefreshSSE() {
  stopPreviewRefreshSSE()
  const url = `${window.location.origin}/api/channels/preview-refresh/stream`
  const es = new EventSource(url)
  previewRefreshEventSource = es
  es.addEventListener('refresh_done', () => {
    previewRefreshVersion.value = Date.now()
    stopPreviewRefreshSSE()
  })
  es.onerror = () => stopPreviewRefreshSSE()
}

function stopPreviewRefreshSSE() {
  if (previewRefreshEventSource) {
    previewRefreshEventSource.close()
    previewRefreshEventSource = null
  }
}

async function openPlayer(ch) {
  playerError.value = ''
  playerHlsRetryUsed = false
  playerModal.value = { channelName: ch.display_name || ch.name, ready: false }
  try {
    const data = await api.streamPlaybackStart({ instance_id: ch.instance_id, channel_name: ch.name })
    const playbackUrl = data.playback_url
    const sessionId = data.session_id
    const useNativeVideo = !!data.use_native_video
    const useMpegtsJs = !!data.use_mpegts_js
    const fullUrl = playbackUrl.startsWith('http') ? playbackUrl : `${window.location.origin}${playbackUrl.startsWith('/') ? '' : '/'}${playbackUrl}`
    playerModal.value = { ...playerModal.value, playbackUrl: fullUrl, sessionId, ready: true, useNativeVideo, useMpegtsJs }
    await nextTick()
    attachPlayer(fullUrl, playbackUrl, useNativeVideo, useMpegtsJs)
  } catch (e) {
    playerError.value = e?.message || 'Не удалось запустить воспроизведение'
    playerModal.value = { ...playerModal.value, ready: true }
  }
}

function attachPlayer(fullUrl, playbackUrl, useNativeVideo = false, useMpegtsJs = false) {
  const video = playerVideoEl.value
  if (!video) return
  if (playerHls) {
    playerHls.destroy()
    playerHls = null
  }
  if (playerMpegts) {
    playerMpegts.destroy()
    playerMpegts = null
  }
  video.src = ''
  playerError.value = ''
  if (useMpegtsJs) {
    if (mpegts.isSupported()) {
      playerMpegts = mpegts.createPlayer(
        { type: 'mse', isLive: true, url: fullUrl },
        { isLive: true }
      )
      playerMpegts.attachMediaElement(video)
      playerMpegts.on(mpegts.Events.ERROR, (_, data) => {
        const msg = data?.message || data?.reason || 'Ошибка потока'
        playerError.value = typeof msg === 'string' ? msg.slice(0, 120) : 'Ошибка загрузки потока'
      })
      playerMpegts.load()
      playerMpegts.play()
    } else {
      playerError.value = 'Воспроизведение MPEG-TS не поддерживается в этом браузере'
    }
  } else if (!useNativeVideo && (playbackUrl.includes('.m3u8') || playbackUrl.includes('/streams/') || playbackUrl.includes('/streams/proxy/'))) {
    if (Hls.isSupported()) {
      playerHls = new Hls(hlsConfig)
      playerHls.loadSource(fullUrl)
      playerHls.attachMedia(video)
      playerHls.on(Hls.Events.ERROR, (_, data) => {
        if (!data.fatal) return
        if (!playerHlsRetryUsed) {
          playerHlsRetryUsed = true
          playerHls.destroy()
          playerHls = null
          setTimeout(() => attachPlayer(fullUrl, playbackUrl, useNativeVideo, useMpegtsJs), 800)
          return
        }
        playerError.value = 'Ошибка загрузки потока'
      })
    } else if (video.canPlayType('application/vnd.apple.mpegurl')) {
      video.src = fullUrl
    } else {
      playerError.value = 'HLS не поддерживается в этом браузере'
    }
  } else {
    video.src = fullUrl
  }
  video.play().catch(() => {})
}

function togglePlayerFullscreen() {
  const video = playerVideoEl.value
  if (!video) return
  if (document.fullscreenElement) {
    document.exitFullscreen?.()
  } else {
    video.requestFullscreen?.()
  }
}

async function closePlayer() {
  if (document.fullscreenElement) {
    document.exitFullscreen?.()
  }
  if (playerModal.value?.sessionId) {
    try {
      await api.streamPlaybackStop(playerModal.value.sessionId)
    } catch (_) {}
  }
  if (playerHls) {
    playerHls.destroy()
    playerHls = null
  }
  if (playerMpegts) {
    playerMpegts.destroy()
    playerMpegts = null
  }
  if (playerVideoEl.value) playerVideoEl.value.src = ''
  playerModal.value = null
  playerError.value = ''
}

async function restart(ch) {
  actioning.value = true
  try {
    await api.channelKill(ch.instance_id, ch.name, true)
    await load()
  } catch (e) {
    alert(e.message)
  } finally {
    actioning.value = false
  }
}

async function kill(ch) {
  actioning.value = true
  try {
    await api.channelKill(ch.instance_id, ch.name, false)
    await load()
  } catch (e) {
    alert(e.message)
  } finally {
    actioning.value = false
  }
}

async function switchInput(ch) {
  actioning.value = true
  try {
    const data = await api.channelInputs(ch.instance_id, ch.name)
    if (data?.inputs?.length > 1) {
      alert(`Входов: ${data.inputs.length}, активный: ${data.active_input ?? 0}. Переключение — через API Astra.`)
    } else {
      alert('Один вход или данных нет.')
    }
  } catch (e) {
    alert(e.message)
  } finally {
    actioning.value = false
  }
}

onMounted(load)

onBeforeUnmount(() => {
  stopPreviewRefreshSSE()
  try {
    stopInlinePlayback()
  } catch (_) {}
})
</script>
