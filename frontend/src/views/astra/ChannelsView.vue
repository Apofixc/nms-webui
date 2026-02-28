<template>
  <div class="p-4 sm:p-6 lg:p-8 w-full min-w-0 max-w-7xl 2xl:max-w-[90rem] mx-auto">
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
            class="rounded-lg px-4 py-2 text-sm font-medium bg-surface-700 text-slate-300 hover:bg-surface-600 hover:text-white disabled:opacity-50 transition-colors"
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

    <!-- Таблица -->
    <div v-else-if="viewMode === 'table'" class="w-full min-w-0 overflow-x-auto rounded-xl border border-surface-700 bg-surface-800/60">
      <table class="w-full text-sm" style="table-layout: fixed; min-width: 600px;">
        <colgroup>
          <col style="width: 160px" />
          <col style="width: 112px" />
          <col style="width: 344px" />
          <col style="width: 120px" />
        </colgroup>
        <thead>
          <tr class="border-b border-surface-700 text-left text-slate-400">
            <th class="px-4 py-3.5 font-medium cursor-pointer hover:text-white transition-colors select-none" @click="toggleSort">
              Имя <span class="ml-1 text-accent">{{ sortDirection === 'asc' ? '↑' : '↓' }}</span>
            </th>
            <th class="px-3 py-3.5 font-medium">Превью</th>
            <th class="px-4 py-3.5 font-medium">Список выходов</th>
            <th class="px-4 py-3.5 font-medium pr-5">Действия</th>
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
                  <span class="text-slate-500 text-sm font-normal tabular-nums">{{ group.channels.length }} {{ pluralChannels(group.channels.length) }}</span>
                </div>
              </td>
            </tr>
            <tr
              v-for="ch in group.channels"
              :key="channelKey(ch)"
              class="border-t border-surface-700/50 hover:bg-surface-750/30 transition-colors"
            >
              <td class="px-4 py-3 align-middle min-h-[72px]">
                <span class="block truncate max-w-full text-white" :title="ch.display_name ? `API: ${ch.name}` : ''">{{ ch.display_name || ch.name }}</span>
              </td>
              <td class="px-3 py-3 align-middle min-h-[72px]">
                <div class="relative inline-block w-24 h-14 rounded-lg overflow-hidden bg-surface-700 border border-surface-600 flex-shrink-0">
                  <img
                    v-if="getPreviewUrl(ch)"
                    :src="getPreviewUrl(ch) || ''"
                    class="absolute inset-0 w-full h-full object-cover"
                    loading="lazy"
                  />
                  <span v-else class="absolute inset-0 flex items-center justify-center text-slate-500 text-xs">—</span>
                </div>
              </td>
              <td class="px-4 py-3 align-middle min-h-[72px]">
                <div class="relative">
                  <template v-if="(ch.output || []).length">
                    <button
                      type="button"
                      class="text-accent hover:underline text-left text-sm"
                      @click.stop="toggleOutputDropdown(channelKey(ch))"
                    >
                      Список адресов выходов ({{ (ch.output || []).length }})
                    </button>
                    <div
                      v-if="expandedOutputKey === channelKey(ch)"
                      class="absolute left-0 top-full mt-1 z-10 min-w-[200px] max-w-[320px] rounded-lg border border-surface-600 bg-surface-800 shadow-xl py-2 max-h-60 overflow-y-auto"
                      @click.stop
                    >
                      <button
                        v-for="(url, i) in (ch.output || [])"
                        :key="i"
                        type="button"
                        class="block w-full text-left px-3 py-1.5 text-sm text-accent hover:bg-surface-700 truncate flex items-center gap-2 group"
                        :title="url"
                        @click.stop.prevent="closeOutputDropdown(); playUrl(url, ch.name)"
                      >
                        <svg xmlns="http://www.w3.org/2000/svg" class="w-4 h-4 opacity-50 group-hover:opacity-100 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z" /><path stroke-linecap="round" stroke-linejoin="round" d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>
                        <span class="truncate">{{ url }}</span>
                      </button>
                    </div>
                  </template>
                  <span v-else class="text-slate-500">—</span>
                </div>
              </td>
              <td class="px-4 py-3 align-middle w-[120px] pr-5">
                <div class="flex gap-1.5 flex-shrink-0">
                  <button type="button" title="Перезапуск" class="rounded-lg bg-surface-700 text-slate-300 p-2 hover:bg-surface-600 disabled:opacity-50" :disabled="actioning" @click="restart(ch)">
                    <svg xmlns="http://www.w3.org/2000/svg" class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" /></svg>
                  </button>
                  <button type="button" title="Отключить" class="rounded-lg bg-danger/20 text-danger border border-danger/40 p-2 hover:bg-danger/30 disabled:opacity-50" :disabled="actioning" @click="kill(ch)">
                    <svg xmlns="http://www.w3.org/2000/svg" class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M18.36 6.64a9 9 0 11-12.73 0M12 2v10" /></svg>
                  </button>
                </div>
              </td>
            </tr>
          </template>
        </template>
        <tbody v-else>
          <tr v-for="ch in channels" :key="channelKey(ch)" class="border-t border-surface-700/50 hover:bg-surface-750/30 transition-colors">
            <td class="px-4 py-3 align-middle min-h-[72px]">
              <span class="block truncate max-w-full text-white" :title="ch.display_name ? `API: ${ch.name}` : ''">{{ ch.display_name || ch.name }}</span>
            </td>
              <td class="px-3 py-3 align-middle min-h-[72px]">
                <div class="relative inline-block w-24 h-14 rounded-lg overflow-hidden bg-surface-700 border border-surface-600 flex-shrink-0">
                  <img
                    v-if="getPreviewUrl(ch)"
                    :src="getPreviewUrl(ch) || ''"
                    class="absolute inset-0 w-full h-full object-cover"
                    loading="lazy"
                  />
                  <span v-else class="absolute inset-0 flex items-center justify-center text-slate-500 text-xs">—</span>
                </div>
              </td>
              <td class="px-4 py-3 align-middle min-h-[72px]">
                <div class="relative">
                  <template v-if="(ch.output || []).length">
                    <button
                      type="button"
                      class="text-accent hover:underline text-left text-sm"
                      @click.stop="toggleOutputDropdown(channelKey(ch))"
                    >
                      Список адресов выходов ({{ (ch.output || []).length }})
                    </button>
                    <div
                      v-if="expandedOutputKey === channelKey(ch)"
                      class="absolute left-0 top-full mt-1 z-10 min-w-[200px] max-w-[320px] rounded-lg border border-surface-600 bg-surface-800 shadow-xl py-2 max-h-60 overflow-y-auto"
                      @click.stop
                    >
                      <button
                        v-for="(url, i) in (ch.output || [])"
                        :key="i"
                        type="button"
                        class="block w-full text-left px-3 py-1.5 text-sm text-accent hover:bg-surface-700 truncate flex items-center gap-2 group"
                        :title="url"
                        @click.stop.prevent="closeOutputDropdown(); playUrl(url, ch.name)"
                      >
                        <svg xmlns="http://www.w3.org/2000/svg" class="w-4 h-4 opacity-50 group-hover:opacity-100 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z" /><path stroke-linecap="round" stroke-linejoin="round" d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>
                        <span class="truncate">{{ url }}</span>
                      </button>
                    </div>
                  </template>
                  <span v-else class="text-slate-500">—</span>
                </div>
              </td>
            <td class="px-4 py-3 align-middle w-[120px] pr-5">
              <div class="flex gap-1.5 flex-shrink-0">
                <button type="button" title="Перезапуск" class="rounded-lg bg-surface-700 text-slate-300 p-2 hover:bg-surface-600 disabled:opacity-50" :disabled="actioning" @click="restart(ch)">
                  <svg xmlns="http://www.w3.org/2000/svg" class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" /></svg>
                </button>
                <button type="button" title="Отключить" class="rounded-lg bg-danger/20 text-danger border border-danger/40 p-2 hover:bg-danger/30 disabled:opacity-50" :disabled="actioning" @click="kill(ch)">
                  <svg xmlns="http://www.w3.org/2000/svg" class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M18.36 6.64a9 9 0 11-12.73 0M12 2v10" /></svg>
                </button>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- Карточки -->
    <div v-else class="space-y-6">
      <template v-if="groupByInstance">
        <section v-for="group in groupedChannels" :key="group.port" class="rounded-xl border border-surface-700 bg-surface-800/60">
          <div class="px-4 py-3 flex items-center gap-3 border-b border-surface-700 bg-surface-750/80">
            <span class="w-1 h-5 rounded-full bg-accent flex-shrink-0" />
            <span class="font-mono font-semibold text-accent">:{{ group.port }}</span>
            <span class="text-slate-500 text-sm">Экземпляр · {{ group.channels.length }} {{ pluralChannels(group.channels.length) }}</span>
          </div>
          <div class="p-4 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            <article
              v-for="ch in group.channels"
              :key="channelKey(ch)"
              class="rounded-xl border border-surface-700 bg-surface-750/50 transition-all hover:border-surface-600"
            >
              <p class="p-3 pb-0 font-medium text-white truncate" :title="ch.display_name ? `API: ${ch.name}` : ''">{{ ch.display_name || ch.name }}</p>
              <div class="p-3">
                <div class="relative w-full aspect-video rounded-xl bg-surface-800 border border-surface-600 overflow-hidden ring-1 ring-black/20 shadow-inner group">
                  <template v-if="playingCardKey === channelKey(ch)">
                    <div class="absolute inset-0 z-10 bg-black">
                      <VideoPlayer v-if="cardPlayerUrls[channelKey(ch)]?.url" :url="cardPlayerUrls[channelKey(ch)].url" :type="cardPlayerUrls[channelKey(ch)].type" />
                      <div v-else class="flex w-full h-full items-center justify-center">
                        <svg class="animate-spin h-8 w-8 text-accent" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path></svg>
                      </div>
                    </div>
                  </template>
                  <template v-else>
                    <img
                      v-if="getPreviewUrl(ch)"
                      :src="getPreviewUrl(ch) || ''"
                      class="absolute inset-0 w-full h-full object-cover cursor-pointer hover:scale-105 transition-transform duration-500"
                      loading="lazy"
                      @click="toggleCardPlayer(ch)"
                    />
                    <span v-else class="absolute inset-0 flex items-center justify-center text-slate-500 text-sm">—</span>
                    
                    <div
                      v-if="getPreviewUrl(ch)"
                      class="absolute inset-0 flex items-center justify-center bg-black/40 opacity-0 group-hover:opacity-100 transition-opacity cursor-pointer pointer-events-none"
                    >
                      <svg xmlns="http://www.w3.org/2000/svg" class="w-12 h-12 text-white/90 drop-shadow-lg" fill="currentColor" viewBox="0 0 24 24"><path d="M8 5v14l11-7z"/></svg>
                    </div>
                  </template>
                </div>
              </div>
              <div class="px-3 pb-2 min-h-[2.5rem] flex flex-col justify-center">
                <div class="relative">
                  <template v-if="(ch.output || []).length">
                    <button
                      type="button"
                      class="text-accent hover:underline text-left text-sm"
                      @click.stop="toggleOutputDropdown(channelKey(ch))"
                    >
                      Список адресов выходов ({{ (ch.output || []).length }})
                    </button>
                    <div
                      v-if="expandedOutputKey === channelKey(ch)"
                      class="absolute left-0 top-full mt-1 z-20 min-w-[200px] max-w-[320px] rounded-lg border border-surface-600 bg-surface-800 shadow-xl py-2 max-h-60 overflow-y-auto"
                      @click.stop
                    >
                      <button
                        v-for="(url, i) in (ch.output || [])"
                        :key="i"
                        type="button"
                        class="block w-full text-left px-3 py-1.5 text-sm text-accent hover:bg-surface-700 truncate flex items-center gap-2 group"
                        :title="url"
                        @click="closeOutputDropdown(); playUrl(url, ch.name)"
                      >
                        <svg xmlns="http://www.w3.org/2000/svg" class="w-4 h-4 opacity-50 group-hover:opacity-100" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z" /><path stroke-linecap="round" stroke-linejoin="round" d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>
                        <span class="truncate">{{ url }}</span>
                      </button>
                    </div>
                  </template>
                  <span v-else class="text-slate-500 text-xs">—</span>
                </div>
              </div>
              <div class="px-3 pb-3 flex gap-2">
                <button type="button" title="Перезапуск" class="rounded-lg bg-surface-700 text-slate-300 p-2 hover:bg-surface-600 disabled:opacity-50" :disabled="actioning" @click="restart(ch)">
                  <svg xmlns="http://www.w3.org/2000/svg" class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" /></svg>
                </button>
                <button type="button" title="Отключить" class="rounded-lg bg-danger/20 text-danger border border-danger/40 p-2 hover:bg-danger/30 disabled:opacity-50" :disabled="actioning" @click="kill(ch)">
                  <svg xmlns="http://www.w3.org/2000/svg" class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M18.36 6.64a9 9 0 11-12.73 0M12 2v10" /></svg>
                </button>
              </div>
            </article>
          </div>
        </section>
      </template>
      <div v-else class="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        <article
          v-for="ch in channels"
          :key="channelKey(ch)"
          class="rounded-xl border border-surface-700 bg-surface-800/60 transition-all hover:border-surface-600"
        >
          <p class="p-3 pb-0 font-medium text-white truncate" :title="ch.display_name ? `API: ${ch.name}` : ''">{{ ch.display_name || ch.name }}</p>
          <div class="p-3">
            <div class="relative w-full aspect-video rounded-xl bg-surface-800 border border-surface-600 overflow-hidden ring-1 ring-black/20 shadow-inner group">
              <template v-if="playingCardKey === channelKey(ch)">
                <div class="absolute inset-0 z-10 bg-black">
                  <VideoPlayer v-if="cardPlayerUrls[channelKey(ch)]?.url" :url="cardPlayerUrls[channelKey(ch)].url" :type="cardPlayerUrls[channelKey(ch)].type" />
                  <div v-else class="flex w-full h-full items-center justify-center">
                    <svg class="animate-spin h-8 w-8 text-accent" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path></svg>
                  </div>
                </div>
              </template>
              <template v-else>
                <img
                  v-if="getPreviewUrl(ch)"
                  :src="getPreviewUrl(ch) || ''"
                  class="absolute inset-0 w-full h-full object-cover cursor-pointer hover:scale-105 transition-transform duration-500"
                  loading="lazy"
                  @click="toggleCardPlayer(ch)"
                />
                <span v-else class="absolute inset-0 flex items-center justify-center text-slate-500 text-sm">—</span>
                
                <div
                  v-if="getPreviewUrl(ch)"
                  class="absolute inset-0 flex items-center justify-center bg-black/40 opacity-0 group-hover:opacity-100 transition-opacity cursor-pointer pointer-events-none"
                >
                  <svg xmlns="http://www.w3.org/2000/svg" class="w-12 h-12 text-white/90 drop-shadow-lg" fill="currentColor" viewBox="0 0 24 24"><path d="M8 5v14l11-7z"/></svg>
                </div>
              </template>
            </div>
          </div>
          <div class="px-3 pb-2 min-h-[2.5rem] flex flex-col justify-center">
            <div class="relative">
              <template v-if="(ch.output || []).length">
                <button
                  type="button"
                  class="text-accent hover:underline text-left text-sm"
                  @click.stop="toggleOutputDropdown(channelKey(ch))"
                >
                  Список адресов выходов ({{ (ch.output || []).length }})
                </button>
                <div
                  v-if="expandedOutputKey === channelKey(ch)"
                  class="absolute left-0 top-full mt-1 z-20 min-w-[200px] max-w-[320px] rounded-lg border border-surface-600 bg-surface-800 shadow-xl py-2 max-h-60 overflow-y-auto"
                  @click.stop
                >
                  <button
                    v-for="(url, i) in (ch.output || [])"
                    :key="i"
                    type="button"
                    class="block w-full text-left px-3 py-1.5 text-sm text-accent hover:bg-surface-700 truncate flex items-center gap-2 group"
                    :title="url"
                    @click="closeOutputDropdown(); playUrl(url, ch.name)"
                  >
                    <svg xmlns="http://www.w3.org/2000/svg" class="w-4 h-4 opacity-50 group-hover:opacity-100" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z" /><path stroke-linecap="round" stroke-linejoin="round" d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>
                    <span class="truncate">{{ url }}</span>
                  </button>
                </div>
              </template>
              <span v-else class="text-slate-500 text-xs">—</span>
            </div>
          </div>
          <div class="px-3 pb-3 flex gap-2">
            <button type="button" title="Перезапуск" class="rounded-lg bg-surface-700 text-slate-300 p-2 hover:bg-surface-600 disabled:opacity-50" :disabled="actioning" @click="restart(ch)">
              <svg xmlns="http://www.w3.org/2000/svg" class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" /></svg>
            </button>
            <button type="button" title="Отключить" class="rounded-lg bg-danger/20 text-danger border border-danger/40 p-2 hover:bg-danger/30 disabled:opacity-50" :disabled="actioning" @click="kill(ch)">
              <svg xmlns="http://www.w3.org/2000/svg" class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M18.36 6.64a9 9 0 11-12.73 0M12 2v10" /></svg>
            </button>
          </div>
        </article>
      </div>
    </div>
    
    <!-- Video Player Modal -->
    <div v-if="showPlayer" class="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4 sm:p-6" @click="closePlayer">
      <div class="relative w-full max-w-5xl bg-surface-900 rounded-2xl overflow-hidden shadow-2xl border border-surface-700 flex flex-col" @click.stop>
        <div class="flex items-center justify-between px-4 py-3 bg-surface-800 border-b border-surface-700">
          <h3 class="text-white font-medium truncate pr-4">{{ playerTitle || 'Проигрыватель' }}</h3>
          <button type="button" class="text-slate-400 hover:text-white transition-colors" @click="closePlayer">
            <svg xmlns="http://www.w3.org/2000/svg" class="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>
        <div class="relative w-full aspect-video bg-black">
          <VideoPlayer v-if="showPlayer" :url="playerUrl" :type="playerType" />
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onBeforeUnmount, nextTick } from 'vue'
import http, { fetchModuleSettingsDefinition } from '@/core/api'
import VideoPlayer from '@/components/ui/VideoPlayer.vue'

const loading = ref(true)
const actioning = ref(false)
const channels = ref<any[]>([])
const viewMode = ref<'table' | 'cards'>('table')
const groupByInstance = ref(false)
const sortDirection = ref<'asc' | 'desc'>('asc')

const playOutputFormat = ref('http_ts')
const previewTimestamp = ref(Date.now())
// Video Player State
const showPlayer = ref(false)
const playerUrl = ref('')
const playerTitle = ref('')

// In-card player state
const playingCardKey = ref<string | null>(null)
const cardPlayerUrls = ref<Record<string, { url: string, type: string }>>({})

const previewRefreshSeconds = 10 // Интервал обновления превью

function toggleSort() {
  sortDirection.value = sortDirection.value === 'asc' ? 'desc' : 'asc'
  channels.value.sort((a: any, b: any) => {
    const nameA = a.display_name || a.name || ''
    const nameB = b.display_name || b.name || ''
    return sortDirection.value === 'asc' 
      ? nameA.localeCompare(nameB) 
      : nameB.localeCompare(nameA)
  })
}

const expandedOutputKey = ref<string | null>(null)
let outputDropdownClickOutside: (() => void) | null = null

function channelKey(ch: any) {
  return `${ch.instance_id}:${ch.name}`
}

function getFirstOutput(ch: any) {
  if (ch.output && ch.output.length > 0) {
    return ch.output[0]
  }
  return null
}

function getPreviewUrl(ch: any) {
  const url = getFirstOutput(ch)
  if (!url) return null
  return `/api/modules/stream/v1/preview?url=${encodeURIComponent(url)}&t=${previewTimestamp.value}`
}

async function prepareStreamUrl(url: string) {
  try {
    const { data } = await http.post(`/api/modules/stream/v1/start?url=${encodeURIComponent(url)}&output_type=${playOutputFormat.value}`)
    return { url: data.output_url, type: data.output_type }
  } catch (err) {
    console.error('Failed to start stream', err)
    return null
  }
}

async function stopStreamUrl(url: string) {
  try {
    await http.post(`/api/modules/stream/v1/stop?url=${encodeURIComponent(url)}`)
  } catch (err) {
    console.error('Failed to stop stream', err)
  }
}

const playerType = ref('http_ts')

async function playUrl(url: string, title: string) {
  playerTitle.value = title
  const result = await prepareStreamUrl(url)
  if (result) {
    playerUrl.value = result.url.startsWith('/') ? `${window.location.origin}${result.url}` : result.url
    playerType.value = result.type
    showPlayer.value = true
  }
}

async function closePlayer() {
  showPlayer.value = false
  playerUrl.value = ''
  playerTitle.value = ''
}

async function toggleCardPlayer(ch: any) {
  const key = channelKey(ch)
  if (playingCardKey.value === key) {
    playingCardKey.value = null
    const old = cardPlayerUrls.value[key]
    if (old && old.url) stopStreamUrl(old.url)
    delete cardPlayerUrls.value[key]
  } else {
    // Включаем плеер для этой карточки, выключаем остальные (чтобы не перегружать клиент)
    const oldKey = playingCardKey.value
    if (oldKey) {
      const old = cardPlayerUrls.value[oldKey]
      if (old && old.url) stopStreamUrl(old.url)
      delete cardPlayerUrls.value[oldKey]
    }
    playingCardKey.value = key
    cardPlayerUrls.value[key] = { url: '', type: playOutputFormat.value } // Показываем лоадер плеера
    const url = getFirstOutput(ch)
    if (url) {
      const result = await prepareStreamUrl(url)
      if (result && playingCardKey.value === key) {
        cardPlayerUrls.value[key] = {
          url: result.url.startsWith('/') ? `${window.location.origin}${result.url}` : result.url,
          type: result.type
        }
      }
    }
  }
}

const groupedChannels = computed(() => {
  const map = new Map<number, any[]>()
  for (const ch of channels.value) {
    const port = ch.instance_port ?? 0
    if (!map.has(port)) map.set(port, [])
    map.get(port)!.push(ch)
  }
  return [...map.entries()]
    .sort((a, b) => a[0] - b[0])
    .map(([port, chs]) => {
      chs.sort((a, b) => {
        const nameA = a.display_name || a.name || ''
        const nameB = b.display_name || b.name || ''
        return sortDirection.value === 'asc' 
          ? nameA.localeCompare(nameB) 
          : nameB.localeCompare(nameA)
      })
      return { port, channels: chs }
    })
})

function pluralChannels(n: number) {
  if (n === 1) return 'канал'
  if (n >= 2 && n <= 4) return 'канала'
  return 'каналов'
}

async function load() {
  loading.value = true
  try {
    const { data } = await http.get('/api/aggregate/channels')
    let fetched = data?.channels || []
    fetched.sort((a: any, b: any) => {
      const nameA = a.display_name || a.name || ''
      const nameB = b.display_name || b.name || ''
      return sortDirection.value === 'asc' 
        ? nameA.localeCompare(nameB) 
        : nameB.localeCompare(nameA)
    })
    channels.value = fetched
  } catch {
    channels.value = []
  } finally {
    loading.value = false
  }
}

function toggleOutputDropdown(key: string) {
  const next = expandedOutputKey.value === key ? null : key
  expandedOutputKey.value = next
  if (outputDropdownClickOutside) {
    document.removeEventListener('click', outputDropdownClickOutside)
    outputDropdownClickOutside = null
  }
  if (next) {
    nextTick(() => {
      outputDropdownClickOutside = () => {
        expandedOutputKey.value = null
        if (outputDropdownClickOutside) document.removeEventListener('click', outputDropdownClickOutside)
        outputDropdownClickOutside = null
      }
      setTimeout(() => { if (outputDropdownClickOutside) document.addEventListener('click', outputDropdownClickOutside) }, 0)
    })
  }
}

function closeOutputDropdown() {
  expandedOutputKey.value = null
  if (outputDropdownClickOutside) {
    document.removeEventListener('click', outputDropdownClickOutside)
    outputDropdownClickOutside = null
  }
}

async function restart(ch: any) {
  if (!ch || actioning.value) return
  actioning.value = true
  try {
    await http.post(`/api/instances/${ch.instance_id}/channels/${encodeURIComponent(ch.name)}/restart`)
  } catch (err: any) {
    console.error('Restart failed', err)
  } finally {
    actioning.value = false
  }
}

async function kill(ch: any) {
  if (!ch || actioning.value) return
  actioning.value = true
  try {
    await http.post(`/api/instances/${ch.instance_id}/channels/${encodeURIComponent(ch.name)}/stop`)
  } catch (err: any) {
    console.error('Stop failed', err)
  } finally {
    actioning.value = false
  }
}

let previewTimer: number | null = null

onMounted(async () => {
  try {
    const streamDef = await fetchModuleSettingsDefinition('stream')
    if (streamDef) {
      playOutputFormat.value = streamDef.current?.default_browser_player_format || streamDef.defaults?.default_browser_player_format || 'http_ts'
    }
  } catch (err) {
    console.warn("Could not load stream module settings", err)
  }

  load()
  previewTimer = window.setInterval(() => {
    previewTimestamp.value = Date.now()
  }, previewRefreshSeconds * 1000)
})

onBeforeUnmount(() => {
  if (previewTimer) clearInterval(previewTimer)
})
</script>
