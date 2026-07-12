<template>
  <div class="p-6 space-y-6 animate-fade-in">
    <!-- Заголовок -->
    <div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
      <div>
        <h1 class="text-2xl font-bold text-white tracking-tight">Управление Astra</h1>
        <p class="mt-1 text-sm text-slate-400">Настройка каналов, DVB-адаптеров и управление runtime-конфигурацией</p>
      </div>
      <!-- Выбор экземпляра -->
      <div class="flex items-center gap-2 self-start sm:self-auto">
        <span class="text-xs font-semibold text-slate-450 uppercase tracking-wider">Экземпляр:</span>
        <select
          v-model="selectedInstance"
          @change="onInstanceChange"
          class="px-3 py-1.5 text-sm rounded-lg bg-surface-750 border border-surface-650 text-white focus:outline-none focus:border-accent"
        >
          <option value="" disabled>Выберите экземпляр</option>
          <option
            v-for="inst in instances"
            :key="inst.index"
            :value="inst.index"
          >
            {{ inst.label }} {{ inst.online ? '(Онлайн)' : '(Офлайн)' }}
          </option>
        </select>
      </div>
    </div>

    <!-- Заглушка, если инстанс не выбран или офлайн -->
    <div v-if="!selectedInstanceInfo || !selectedInstanceInfo.online" class="flex flex-col items-center justify-center p-16 rounded-xl border border-surface-700 bg-surface-800/20 text-center">
      <div class="w-16 h-16 rounded-2xl bg-surface-700/50 flex items-center justify-center mb-4">
        <svg xmlns="http://www.w3.org/2000/svg" class="w-8 h-8 text-slate-550" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5">
          <path stroke-linecap="round" stroke-linejoin="round" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
          <path stroke-linecap="round" stroke-linejoin="round" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
        </svg>
      </div>
      <h3 class="text-lg font-semibold text-white mb-1">Управление недоступно</h3>
      <p class="text-sm text-slate-400 max-w-sm">
        {{ selectedInstance === '' ? 'Пожалуйста, выберите активный экземпляр Astra в правом верхнем углу.' : 'Выбранный экземпляр Astra сейчас не в сети.' }}
      </p>
    </div>

    <!-- Основной интерфейс управления -->
    <div v-else class="grid grid-cols-1 lg:grid-cols-2 gap-6">
      
      <!-- Раздел каналов -->
      <Card title="Каналы (Runtime)" padded>
        <template #header>
          <div class="flex justify-between items-center w-full">
            <h3 class="text-lg font-semibold text-white">Каналы (Runtime)</h3>
            <Button variant="primary" size="sm" @click="openAddChannelModal">
              <svg xmlns="http://www.w3.org/2000/svg" class="w-4 h-4 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                <path stroke-linecap="round" stroke-linejoin="round" d="M12 4v16m8-8H4" />
              </svg>
              Добавить канал
            </Button>
          </div>
        </template>

        <div v-if="loading" class="space-y-3 py-4">
          <div v-for="i in 3" :key="i" class="h-12 bg-surface-750/30 rounded-lg animate-pulse" />
        </div>

        <div v-else-if="currentChannels.length === 0" class="text-center py-8 text-slate-500 text-sm">
          Нет добавленных runtime-каналов.
        </div>

        <div v-else class="space-y-3 max-h-[60vh] overflow-y-auto pr-1">
          <div
            v-for="chan in currentChannels"
            :key="chan.name"
            class="flex items-center justify-between p-3 rounded-lg border border-surface-700 bg-surface-750/30 hover:border-surface-650 transition-colors"
          >
            <div class="min-w-0 flex-1">
              <div class="font-semibold text-white truncate">{{ chan.name }}</div>
              <div class="flex flex-col gap-0.5 text-[10px] font-mono text-slate-400 mt-1 truncate">
                <div>Вход: {{ chan.inputs[0] || 'нет' }}</div>
                <div>Выход: {{ chan.outputs[0] || 'нет' }}</div>
              </div>
            </div>
            <Button
              variant="danger"
              size="sm"
              class="ml-3 h-8 px-2.5 text-xs flex items-center justify-center shrink-0"
              :loading="deletingItem === `channel-${chan.name}`"
              @click="deleteChannel(chan.name)"
            >
              Удалить
            </Button>
          </div>
        </div>
      </Card>

      <!-- Раздел адаптеров -->
      <Card title="DVB-адаптеры (Runtime)" padded>
        <template #header>
          <div class="flex justify-between items-center w-full">
            <h3 class="text-lg font-semibold text-white">DVB-адаптеры (Runtime)</h3>
            <Button variant="primary" size="sm" @click="openAddAdapterModal">
              <svg xmlns="http://www.w3.org/2000/svg" class="w-4 h-4 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                <path stroke-linecap="round" stroke-linejoin="round" d="M12 4v16m8-8H4" />
              </svg>
              Добавить адаптер
            </Button>
          </div>
        </template>

        <div v-if="loading" class="space-y-3 py-4">
          <div v-for="i in 3" :key="i" class="h-12 bg-surface-750/30 rounded-lg animate-pulse" />
        </div>

        <div v-else-if="currentAdapters.length === 0" class="text-center py-8 text-slate-500 text-sm">
          Нет добавленных runtime-адаптеров.
        </div>

        <div v-else class="space-y-3 max-h-[60vh] overflow-y-auto pr-1">
          <div
            v-for="adap in currentAdapters"
            :key="adap.name"
            class="flex items-center justify-between p-3 rounded-lg border border-surface-700 bg-surface-750/30 hover:border-surface-650 transition-colors"
          >
            <div class="min-w-0 flex-1">
              <div class="font-semibold text-white truncate">{{ adap.name }}</div>
              <div class="flex gap-2 text-[10px] font-mono text-slate-400 mt-1">
                <span>ID: {{ adap.adapter_id }}</span>
                <span>•</span>
                <span>DVB-{{ adap.type }}</span>
              </div>
            </div>
            <Button
              variant="danger"
              size="sm"
              class="ml-3 h-8 px-2.5 text-xs flex items-center justify-center shrink-0"
              :loading="deletingItem === `adapter-${adap.name}`"
              @click="deleteAdapter(adap.name)"
            >
              Удалить
            </Button>
          </div>
        </div>
      </Card>

    </div>

    <!-- Модальное окно: Добавить канал (выбор полей) -->
    <div v-if="addChannelOpen" class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-fade-in-fast font-sans">
      <div class="w-full max-w-lg p-6 rounded-xl border border-surface-700 bg-surface-800 shadow-xl space-y-6 animate-fade-in-fast max-h-[90vh] overflow-y-auto">
        <div class="flex items-start justify-between">
          <div>
            <h3 class="text-lg font-semibold text-white">Добавить ТВ-канал</h3>
            <p class="text-xs text-slate-400 mt-1">Заполните поля для автоматической генерации параметров Astra</p>
          </div>
          <button @click="closeAddChannelModal" class="text-slate-455 hover:text-white text-lg">&times;</button>
        </div>

        <form @submit.prevent="submitAddChannel" class="space-y-4 text-sm">
          
          <!-- Название канала -->
          <div>
            <label class="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-1.5">Название канала</label>
            <input
              type="text"
              v-model="channelForm.name"
              placeholder="Например, HTB"
              class="w-full px-3 py-2 text-sm rounded-lg bg-surface-750 border border-surface-650 text-white placeholder-slate-550 focus:outline-none focus:border-accent"
              required
            />
          </div>

          <!-- Источник входа -->
          <div class="p-3 rounded-lg border border-surface-700 bg-surface-850/45 space-y-3">
            <span class="text-xs font-bold text-slate-450 uppercase tracking-wider">Входной сигнал</span>
            
            <div>
              <label class="block text-xs text-slate-400 mb-1">Тип входа</label>
              <select
                v-model="channelForm.inputType"
                class="w-full px-3 py-2 text-sm rounded-lg bg-surface-750 border border-surface-650 text-white focus:outline-none focus:border-accent"
              >
                <option value="dvb">DVB Адаптер (тюнер)</option>
                <option value="http">HTTP/HTTPS поток (из сети)</option>
                <option value="udp">UDP мультикаст (из локальной сети)</option>
                <option value="file">MPEG-TS Файл (локальный путь)</option>
              </select>
            </div>

            <!-- Специфичные поля входа -->
            <!-- DVB -->
            <div v-if="channelForm.inputType === 'dvb'" class="grid grid-cols-2 gap-4">
              <div>
                <label class="block text-xs text-slate-400 mb-1">DVB Адаптер</label>
                <select
                  v-model="channelForm.dvbAdapter"
                  class="w-full px-3 py-2 text-sm rounded-lg bg-surface-750 border border-surface-650 text-white focus:outline-none focus:border-accent"
                  required
                >
                  <option value="" disabled>Выберите адаптер</option>
                  <option
                    v-for="adap in currentAdapters"
                    :key="adap.name"
                    :value="adap.name"
                  >
                    {{ adap.name }}
                  </option>
                </select>
              </div>
              <div>
                <label class="block text-xs text-slate-400 mb-1">PNR (Program Number)</label>
                <input
                  type="number"
                  v-model.number="channelForm.dvbPnr"
                  placeholder="e.g. 420"
                  class="w-full px-3 py-2 text-sm rounded-lg bg-surface-750 border border-surface-650 text-white placeholder-slate-555 focus:outline-none focus:border-accent"
                  required
                />
              </div>
            </div>

            <!-- HTTP -->
            <div v-if="channelForm.inputType === 'http'">
              <label class="block text-xs text-slate-400 mb-1">Ссылка на поток (URL)</label>
              <input
                type="url"
                v-model="channelForm.httpUrl"
                placeholder="http://server.com:8000/stream"
                class="w-full px-3 py-2 text-sm rounded-lg bg-surface-750 border border-surface-650 text-white placeholder-slate-550 focus:outline-none focus:border-accent"
                required
              />
            </div>

            <!-- UDP -->
            <div v-if="channelForm.inputType === 'udp'" class="grid grid-cols-3 gap-3">
              <div class="col-span-2">
                <label class="block text-xs text-slate-400 mb-1">IP Мультикаста</label>
                <input
                  type="text"
                  v-model="channelForm.udpIp"
                  placeholder="239.100.1.1"
                  class="w-full px-3 py-2 text-sm rounded-lg bg-surface-750 border border-surface-650 text-white placeholder-slate-550 focus:outline-none focus:border-accent"
                  required
                />
              </div>
              <div>
                <label class="block text-xs text-slate-400 mb-1">Порт</label>
                <input
                  type="number"
                  v-model.number="channelForm.udpPort"
                  placeholder="1234"
                  class="w-full px-3 py-2 text-sm rounded-lg bg-surface-750 border border-surface-650 text-white placeholder-slate-550 focus:outline-none focus:border-accent"
                  required
                />
              </div>
            </div>

            <!-- MPEG-TS File -->
            <div v-if="channelForm.inputType === 'file'" class="space-y-2">
              <div>
                <label class="block text-xs text-slate-400 mb-1">Абсолютный путь к файлу (.ts)</label>
                <input
                  type="text"
                  v-model="channelForm.filePath"
                  placeholder="/opt/media/video.ts"
                  class="w-full px-3 py-2 text-sm rounded-lg bg-surface-750 border border-surface-650 text-white placeholder-slate-550 focus:outline-none focus:border-accent font-mono"
                  required
                />
              </div>
              <div class="flex items-center gap-2">
                <input type="checkbox" id="fileLoop" v-model="channelForm.fileLoop" class="rounded bg-surface-750 text-accent" />
                <label for="fileLoop" class="text-xs text-slate-300 select-none font-semibold">Зациклить воспроизведение (loop)</label>
              </div>
            </div>

            <!-- Раздел: Дополнительные настройки входа (Декодирование и сетевые буферы) -->
            <div>
              <button
                type="button"
                @click="channelForm.showAdvancedInput = !channelForm.showAdvancedInput"
                class="text-xs text-accent hover:underline flex items-center gap-1 font-semibold"
              >
                {{ channelForm.showAdvancedInput ? 'Скрыть' : 'Показать' }} параметры декодирования и настройки входа
                <span class="text-[10px]">{{ channelForm.showAdvancedInput ? '▲' : '▼' }}</span>
              </button>

              <div v-show="channelForm.showAdvancedInput" class="mt-2.5 p-3 rounded bg-surface-800 border border-surface-700/80 space-y-3">
                <!-- Декодирование (Softcam, CAM, BISS) -->
                <div class="border-b border-surface-700 pb-3.5 space-y-3">
                  <div class="text-[10px] text-slate-450 uppercase tracking-wider font-bold">Декодирование (Дешифрование)</div>
                  
                  <div class="grid grid-cols-2 gap-3">
                    <div class="flex items-center gap-2">
                      <input type="checkbox" id="ctrlChanUseCam" v-model="channelForm.useCam" class="rounded bg-surface-750 text-accent" />
                      <label for="ctrlChanUseCam" class="text-xs text-slate-300 select-none">CAM-модуль (DVB-CI)</label>
                    </div>
                    <div class="flex items-center gap-2">
                      <input type="checkbox" id="ctrlChanUseBiss" v-model="channelForm.useBiss" class="rounded bg-surface-750 text-accent" />
                      <label for="ctrlChanUseBiss" class="text-xs text-slate-300 select-none">BISS Дешифрование</label>
                    </div>
                  </div>

                  <div v-if="channelForm.useBiss">
                    <label class="block text-[10px] text-slate-400 mb-1 font-semibold uppercase">Ключ BISS (16 HEX)</label>
                    <input
                      type="text"
                      v-model="channelForm.bissKey"
                      placeholder="1122330044556600"
                      maxlength="16"
                      class="w-full px-2.5 py-1.5 text-xs rounded bg-surface-750 border border-surface-650 text-white font-mono"
                    />
                  </div>

                  <div class="space-y-1.5">
                    <div class="flex items-center gap-2">
                      <input type="checkbox" id="ctrlChanUseSoftcam" v-model="channelForm.useSoftcam" class="rounded bg-surface-750 text-accent" />
                      <label for="ctrlChanUseSoftcam" class="text-xs text-slate-300 select-none">Softcam (newcamd ридер)</label>
                    </div>
                    <div v-if="channelForm.useSoftcam">
                      <label class="block text-[10px] text-slate-400 mb-1 font-semibold uppercase">Имя ридера (из Astra)</label>
                      <input
                        type="text"
                        v-model="channelForm.softcamReader"
                        placeholder="e.g. reader_0"
                        class="w-full px-2.5 py-1.5 text-xs rounded bg-surface-750 border border-surface-650 text-white font-mono"
                      />
                    </div>
                  </div>
                </div>

                <!-- Фильтрация служебных таблиц -->
                <div class="border-b border-surface-700 pb-3 space-y-2">
                  <div class="text-[10px] text-slate-450 uppercase tracking-wider font-bold">Таблицы и парсинг</div>
                  <div class="grid grid-cols-2 gap-2">
                    <div class="flex items-center gap-2">
                      <input type="checkbox" id="ctrlPassSdt" v-model="channelForm.passSdt" class="rounded bg-surface-750 text-accent" />
                      <label for="ctrlPassSdt" class="text-xs text-slate-300 select-none">SDT без изменений</label>
                    </div>
                    <div class="flex items-center gap-2">
                      <input type="checkbox" id="ctrlPassEit" v-model="channelForm.passEit" class="rounded bg-surface-750 text-accent" />
                      <label for="ctrlPassEit" class="text-xs text-slate-300 select-none">EIT без изменений</label>
                    </div>
                  </div>
                  <div class="flex items-center gap-2">
                    <input type="checkbox" id="ctrlNoReload" v-model="channelForm.noReload" class="rounded bg-surface-750 text-accent" />
                    <label for="ctrlNoReload" class="text-xs text-slate-300 select-none">Отключить отслеживание изменений потока</label>
                  </div>
                </div>

                <!-- Сетевые опции входов -->
                <div v-if="channelForm.inputType === 'http'" class="space-y-3">
                  <div class="text-[10px] text-slate-450 uppercase tracking-wider font-bold">Специфичные для HTTP</div>
                  <div>
                    <label class="block text-[10px] text-slate-400 mb-1 font-semibold uppercase">User-Agent</label>
                    <input
                      type="text"
                      v-model="channelForm.httpUa"
                      placeholder="Astra"
                      class="w-full px-2.5 py-1.5 text-xs rounded bg-surface-750 border border-surface-650 text-white"
                    />
                  </div>
                  <div class="grid grid-cols-2 gap-2">
                    <div>
                      <label class="block text-[10px] text-slate-400 mb-1 font-semibold uppercase">Таймаут (сек)</label>
                      <input
                        type="number"
                        v-model.number="channelForm.httpTimeout"
                        placeholder="10"
                        class="w-full px-2.5 py-1.5 text-xs rounded bg-surface-750 border border-surface-650 text-white"
                      />
                    </div>
                    <div>
                      <label class="block text-[10px] text-slate-400 mb-1 font-semibold uppercase">Буфер приема (КБ)</label>
                      <input
                        type="number"
                        v-model.number="channelForm.httpBufferSize"
                        placeholder="1024"
                        class="w-full px-2.5 py-1.5 text-xs rounded bg-surface-750 border border-surface-650 text-white"
                      />
                    </div>
                  </div>
                </div>

                <div v-if="channelForm.inputType === 'udp'">
                  <div class="text-[10px] text-slate-450 uppercase tracking-wider font-bold">Специфичные для UDP</div>
                  <div class="mt-2">
                    <label class="block text-[10px] text-slate-400 mb-1 font-semibold uppercase">Сетевой интерфейс приема</label>
                    <input
                      type="text"
                      v-model="channelForm.udpInterface"
                      placeholder="eth0 или IP"
                      class="w-full px-2.5 py-1.5 text-xs rounded bg-surface-750 border border-surface-650 text-white font-mono"
                    />
                  </div>
                </div>
              </div>
            </div>
          </div>

          <!-- Выходной сигнал -->
          <div class="p-3 rounded-lg border border-surface-700 bg-surface-850/45 space-y-3">
            <span class="text-xs font-bold text-slate-450 uppercase tracking-wider">Выходной сигнал</span>
            
            <div>
              <label class="block text-xs text-slate-400 mb-1">Формат вещания</label>
              <select
                v-model="channelForm.outputType"
                class="w-full px-3 py-2 text-sm rounded-lg bg-surface-750 border border-surface-650 text-white focus:outline-none focus:border-accent"
              >
                <option value="http">HTTP-вещание (для плееров/клиентов)</option>
                <option value="udp">UDP мультикаст (для локальной сети)</option>
                <option value="file">MPEG-TS Файл (запись на диск)</option>
              </select>
            </div>

            <!-- HTTP Выход -->
            <div v-if="channelForm.outputType === 'http'" class="space-y-3">
              <div class="grid grid-cols-3 gap-3">
                <div>
                  <label class="block text-xs text-slate-400 mb-1">Порт</label>
                  <input
                    type="number"
                    v-model.number="channelForm.outHttpPort"
                    placeholder="8001"
                    class="w-full px-3 py-2 text-sm rounded-lg bg-surface-750 border border-surface-650 text-white placeholder-slate-550 focus:outline-none focus:border-accent"
                    required
                  />
                </div>
                <div class="col-span-2">
                  <label class="block text-xs text-slate-400 mb-1">Путь (Path)</label>
                  <input
                    type="text"
                    v-model="channelForm.outHttpPath"
                    placeholder="htb"
                    class="w-full px-3 py-2 text-sm rounded-lg bg-surface-750 border border-surface-650 text-white placeholder-slate-550 focus:outline-none focus:border-accent"
                    required
                  />
                </div>
              </div>

              <div>
                <button
                  type="button"
                  @click="channelForm.showAdvancedOutput = !channelForm.showAdvancedOutput"
                  class="text-xs text-accent hover:underline flex items-center gap-1 font-semibold"
                >
                  {{ channelForm.showAdvancedOutput ? 'Скрыть' : 'Показать' }} дополнительные настройки HTTP-выхода
                  <span class="text-[10px]">{{ channelForm.showAdvancedOutput ? '▲' : '▼' }}</span>
                </button>

                <div v-show="channelForm.showAdvancedOutput" class="mt-2.5 p-3 rounded bg-surface-800 border border-surface-700/80 space-y-3">
                  <div class="grid grid-cols-2 gap-3">
                    <div>
                      <label class="block text-[10px] text-slate-400 mb-1 font-semibold uppercase">Размер буфера (КБ)</label>
                      <input
                        type="number"
                        v-model.number="channelForm.outHttpBufferSize"
                        placeholder="1024"
                        class="w-full px-2.5 py-1.5 text-xs rounded bg-surface-750 border border-surface-650 text-white font-mono"
                      />
                    </div>
                    <div>
                      <label class="block text-[10px] text-slate-400 mb-1 font-semibold uppercase">Наполнение буфера (КБ)</label>
                      <input
                        type="number"
                        v-model.number="channelForm.outHttpBufferFill"
                        placeholder="256"
                        class="w-full px-2.5 py-1.5 text-xs rounded bg-surface-750 border border-surface-650 text-white font-mono"
                      />
                    </div>
                  </div>
                </div>
              </div>
            </div>

            <!-- UDP Выход -->
            <div v-if="channelForm.outputType === 'udp'" class="space-y-3">
              <div class="grid grid-cols-3 gap-3">
                <div class="col-span-2">
                  <label class="block text-xs text-slate-400 mb-1">IP Адрес</label>
                  <input
                    type="text"
                    v-model="channelForm.outUdpIp"
                    placeholder="239.200.1.1"
                    class="w-full px-3 py-2 text-sm rounded-lg bg-surface-750 border border-surface-650 text-white placeholder-slate-550 focus:outline-none focus:border-accent"
                    required
                  />
                </div>
                <div>
                  <label class="block text-xs text-slate-400 mb-1">Порт</label>
                  <input
                    type="number"
                    v-model.number="channelForm.outUdpPort"
                    placeholder="1234"
                    class="w-full px-3 py-2 text-sm rounded-lg bg-surface-750 border border-surface-650 text-white placeholder-slate-550 focus:outline-none focus:border-accent"
                    required
                  />
                </div>
              </div>

              <div>
                <button
                  type="button"
                  @click="channelForm.showAdvancedOutput = !channelForm.showAdvancedOutput"
                  class="text-xs text-accent hover:underline flex items-center gap-1 font-semibold"
                >
                  {{ channelForm.showAdvancedOutput ? 'Скрыть' : 'Показать' }} дополнительные настройки UDP-выхода
                  <span class="text-[10px]">{{ channelForm.showAdvancedOutput ? '▲' : '▼' }}</span>
                </button>

                <div v-show="channelForm.showAdvancedOutput" class="mt-2.5 p-3 rounded bg-surface-800 border border-surface-700/80 space-y-3">
                  <div class="grid grid-cols-2 gap-3">
                    <div>
                      <label class="block text-[10px] text-slate-400 mb-1 font-semibold uppercase">Сетевой интерфейс</label>
                      <input
                        type="text"
                        v-model="channelForm.outUdpInterface"
                        placeholder="e.g. eth0"
                        class="w-full px-2.5 py-1.5 text-xs rounded bg-surface-750 border border-surface-650 text-white font-mono"
                      />
                    </div>
                    <div>
                      <label class="block text-[10px] text-slate-400 mb-1 font-semibold uppercase">TTL</label>
                      <input
                        type="number"
                        v-model.number="channelForm.outUdpTtl"
                        placeholder="32"
                        class="w-full px-2.5 py-1.5 text-xs rounded bg-surface-750 border border-surface-650 text-white font-mono"
                      />
                    </div>
                  </div>
                </div>
              </div>
            </div>

            <!-- MPEG-TS File Выход -->
            <div v-if="channelForm.outputType === 'file'" class="space-y-2">
              <div>
                <label class="block text-xs text-slate-400 mb-1">Абсолютный путь для записи (.ts)</label>
                <input
                  type="text"
                  v-model="channelForm.outFilePath"
                  placeholder="/opt/media/record.ts"
                  class="w-full px-3 py-2 text-sm rounded-lg bg-surface-750 border border-surface-650 text-white placeholder-slate-550 focus:outline-none focus:border-accent font-mono"
                  required
                />
              </div>
              <div class="flex items-center gap-2">
                <input type="checkbox" id="fileAio" v-model="channelForm.fileAio" class="rounded bg-surface-750 text-accent" />
                <label for="fileAio" class="text-xs text-slate-300 select-none font-semibold">Использовать асинхронную запись (aio)</label>
              </div>
            </div>
          </div>

          <!-- Общие расширенные настройки канала Astra -->
          <div>
            <button
              type="button"
              @click="channelForm.showAdvancedChannel = !channelForm.showAdvancedChannel"
              class="text-xs text-accent hover:underline flex items-center gap-1 font-semibold"
            >
              {{ channelForm.showAdvancedChannel ? 'Скрыть' : 'Показать' }} общие параметры канала (маппинг, тайм-ауты)
              <span class="text-[10px]">{{ channelForm.showAdvancedChannel ? '▲' : '▼' }}</span>
            </button>

            <div v-show="channelForm.showAdvancedChannel" class="mt-2.5 p-3 rounded-lg border border-surface-700 bg-surface-850/45 space-y-3">
              <div class="grid grid-cols-2 gap-3">
                <div class="flex items-center gap-2 py-1">
                  <input type="checkbox" id="ctrlChanEnable" v-model="channelForm.enable" class="rounded bg-surface-750 text-accent" />
                  <label for="ctrlChanEnable" class="text-xs text-slate-300 select-none">Канал включен (enable)</label>
                </div>
                <div>
                  <label class="block text-[10px] text-slate-400 mb-1 font-semibold uppercase">Переключение резерва (сек)</label>
                  <input
                    type="number"
                    v-model.number="channelForm.timeout"
                    placeholder="немедленно"
                    class="w-full px-2.5 py-1.5 text-xs rounded bg-surface-750 border border-surface-650 text-white"
                  />
                </div>
              </div>
              <div class="grid grid-cols-2 gap-3">
                <div>
                  <label class="block text-[10px] text-slate-400 mb-1 font-semibold uppercase">Изменить PNR на выходе (set_pnr)</label>
                  <input
                    type="number"
                    v-model.number="channelForm.set_pnr"
                    placeholder="не менять"
                    class="w-full px-2.5 py-1.5 text-xs rounded bg-surface-750 border border-surface-650 text-white font-mono"
                  />
                </div>
                <div>
                  <label class="block text-[10px] text-slate-400 mb-1 font-semibold uppercase">Изменить TSID на выходе (set_tsid)</label>
                  <input
                    type="number"
                    v-model.number="channelForm.set_tsid"
                    placeholder="не менять"
                    class="w-full px-2.5 py-1.5 text-xs rounded bg-surface-750 border border-surface-650 text-white font-mono"
                  />
                </div>
              </div>
              <div class="grid grid-cols-2 gap-3">
                <div>
                  <label class="block text-[10px] text-slate-400 mb-1 font-semibold uppercase">HTTP Keep Active (сек)</label>
                  <input
                    type="number"
                    v-model.number="channelForm.http_keep_active"
                    placeholder="e.g. 0 (сразу) или -1 (всегда)"
                    class="w-full px-2.5 py-1.5 text-xs rounded bg-surface-750 border border-surface-650 text-white font-mono"
                  />
                </div>
                <div>
                  <label class="block text-[10px] text-slate-400 mb-1 font-semibold uppercase">Перемаппинг PID (map)</label>
                  <input
                    type="text"
                    v-model="channelForm.map"
                    placeholder="pmt=100,video=101"
                    class="w-full px-2.5 py-1.5 text-xs rounded bg-surface-750 border border-surface-650 text-white font-mono"
                  />
                </div>
              </div>
              <div class="grid grid-cols-2 gap-3">
                <div>
                  <label class="block text-[10px] text-slate-400 mb-1 font-semibold uppercase">Название канала (SDT)</label>
                  <input
                    type="text"
                    v-model="channelForm.service_name"
                    placeholder="Original"
                    class="w-full px-2.5 py-1.5 text-xs rounded bg-surface-750 border border-surface-650 text-white"
                  />
                </div>
                <div>
                  <label class="block text-[10px] text-slate-400 mb-1 font-semibold uppercase">Провайдер канала (SDT)</label>
                  <input
                    type="text"
                    v-model="channelForm.service_provider"
                    placeholder="Original"
                    class="w-full px-2.5 py-1.5 text-xs rounded bg-surface-750 border border-surface-650 text-white"
                  />
                </div>
              </div>
            </div>
          </div>

          <!-- Мониторинг -->
          <div class="flex items-center gap-2 py-1">
            <input
              type="checkbox"
              id="ctrlChanMonitor"
              v-model="channelForm.monitor"
              class="rounded bg-surface-750 border-surface-650 text-accent focus:ring-accent"
            />
            <label for="ctrlChanMonitor" class="text-xs text-slate-350 select-none">Включить автоматический мониторинг</label>
          </div>

          <div class="flex justify-end gap-3 pt-4 border-t border-surface-700/60">
            <Button variant="ghost" size="sm" @click="closeAddChannelModal">Отмена</Button>
            <Button variant="primary" size="sm" type="submit" :loading="submitting">Создать</Button>
          </div>
        </form>
      </div>
    </div>

    <!-- Модальное окно: Добавить DVB-адаптер (выбор полей) -->
    <div v-if="addAdapterOpen" class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-fade-in-fast font-sans">
      <div class="w-full max-w-md p-6 rounded-xl border border-surface-700 bg-surface-800 shadow-xl space-y-6 animate-fade-in-fast max-h-[90vh] overflow-y-auto">
        <div class="flex items-start justify-between">
          <div>
            <h3 class="text-lg font-semibold text-white">Добавить DVB-адаптер</h3>
            <p class="text-xs text-slate-400 mt-1">Параметры тюнера и настройки транспондера</p>
          </div>
          <button @click="closeAddAdapterModal" class="text-slate-455 hover:text-white text-lg">&times;</button>
        </div>

        <form @submit.prevent="submitAddAdapter" class="space-y-4 text-sm">
          
          <div class="grid grid-cols-2 gap-4">
            <div>
              <label class="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-1.5">Имя адаптера</label>
              <input
                type="text"
                v-model="adapterForm.name"
                placeholder="adapter_0"
                class="w-full px-3 py-2 text-sm rounded-lg bg-surface-750 border border-surface-650 text-white placeholder-slate-550 focus:outline-none focus:border-accent"
                required
              />
            </div>
            <div>
              <label class="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-1.5">ID Адаптера</label>
              <input
                type="number"
                v-model.number="adapterForm.adapter"
                placeholder="0"
                class="w-full px-3 py-2 text-sm rounded-lg bg-surface-750 border border-surface-650 text-white placeholder-slate-550 focus:outline-none focus:border-accent"
                required
              />
            </div>
          </div>

          <div>
            <label class="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-1.5">Тип DVB тюнера</label>
            <select
              v-model="adapterForm.type"
              class="w-full px-3 py-2 text-sm rounded-lg bg-surface-750 border border-surface-650 text-white focus:outline-none focus:border-accent"
            >
              <option value="S">DVB-S / S2 (Спутниковое)</option>
              <option value="T">DVB-T / T2 (Эфирное цифровое)</option>
              <option value="C">DVB-C (Кабельное)</option>
              <option value="ATSC">ATSC (Цифровое США/Канада)</option>
              <option value="ASI">DVB-ASI (Асинхронный интерфейс)</option>
            </select>
          </div>

          <!-- Настройки транспондера в зависимости от типа DVB -->
          <!-- Спутник DVB-S/S2 -->
          <div v-if="adapterForm.type === 'S'" class="p-3 rounded-lg border border-surface-700 bg-surface-850/45 space-y-3">
            <span class="text-xs font-bold text-slate-450 uppercase tracking-wider">Параметры DVB-S/S2</span>
            
            <div class="grid grid-cols-2 gap-4">
              <div>
                <label class="block text-xs text-slate-400 mb-1">Частота (МГц)</label>
                <input
                  type="number"
                  v-model.number="adapterForm.dvbsFreq"
                  placeholder="11605"
                  class="w-full px-3 py-2 text-sm rounded-lg bg-surface-750 border border-surface-650 text-white placeholder-slate-550 focus:outline-none focus:border-accent"
                  required
                />
              </div>
              <div>
                <label class="block text-xs text-slate-400 mb-1">Поляризация</label>
                <select
                  v-model="adapterForm.dvbsPol"
                  class="w-full px-3 py-2 text-sm rounded-lg bg-surface-750 border border-surface-650 text-white focus:outline-none focus:border-accent"
                >
                  <option value="V">V (Вертикальная)</option>
                  <option value="H">H (Горизонтальная)</option>
                  <option value="L">L (Левая круговая)</option>
                  <option value="R">R (Правая круговая)</option>
                </select>
              </div>
            </div>

            <div class="grid grid-cols-2 gap-4">
              <div>
                <label class="block text-xs text-slate-400 mb-1">Скорость (Sym/s)</label>
                <input
                  type="number"
                  v-model.number="adapterForm.dvbsSr"
                  placeholder="43200"
                  class="w-full px-3 py-2 text-sm rounded-lg bg-surface-750 border border-surface-650 text-white placeholder-slate-550 focus:outline-none focus:border-accent"
                  required
                />
              </div>
              <div>
                <label class="block text-xs text-slate-400 mb-1">Параметры LNB</label>
                <input
                  type="text"
                  v-model="adapterForm.dvbsLnb"
                  placeholder="9750:10600:11700"
                  class="w-full px-3 py-2 text-sm rounded-lg bg-surface-750 border border-surface-650 text-white placeholder-slate-550 focus:outline-none focus:border-accent font-mono"
                  required
                />
              </div>
            </div>
          </div>

          <!-- DVB-T/T2 -->
          <div v-else-if="adapterForm.type === 'T'" class="p-3 rounded-lg border border-surface-700 bg-surface-850/45 space-y-3">
            <span class="text-xs font-bold text-slate-450 uppercase tracking-wider">Параметры DVB-T/T2</span>
            
            <div>
              <label class="block text-xs text-slate-400 mb-1">Частота транспондера (МГц)</label>
              <input
                type="number"
                v-model.number="adapterForm.dvbtFreq"
                placeholder="498"
                class="w-full px-3 py-2 text-sm rounded-lg bg-surface-750 border border-surface-650 text-white placeholder-slate-550 focus:outline-none focus:border-accent font-mono"
                required
              />
            </div>
          </div>

          <!-- DVB-C -->
          <div v-else-if="adapterForm.type === 'C'" class="p-3 rounded-lg border border-surface-700 bg-surface-850/45 space-y-3">
            <span class="text-xs font-bold text-slate-450 uppercase tracking-wider">Параметры DVB-C</span>
            
            <div class="grid grid-cols-2 gap-4">
              <div>
                <label class="block text-xs text-slate-400 mb-1">Частота (МГц)</label>
                <input
                  type="number"
                  v-model.number="adapterForm.dvbtFreq"
                  placeholder="360"
                  class="w-full px-3 py-2 text-sm rounded-lg bg-surface-750 border border-surface-650 text-white placeholder-slate-550 focus:outline-none focus:border-accent font-mono"
                  required
                />
              </div>
              <div>
                <label class="block text-xs text-slate-400 mb-1">Скорость (Sym/s)</label>
                <input
                  type="number"
                  v-model.number="adapterForm.dvbcSr"
                  placeholder="6900"
                  class="w-full px-3 py-2 text-sm rounded-lg bg-surface-750 border border-surface-650 text-white placeholder-slate-550 focus:outline-none focus:border-accent font-mono"
                  required
                />
              </div>
            </div>
          </div>

          <!-- ATSC -->
          <div v-else-if="adapterForm.type === 'ATSC'" class="p-3 rounded-lg border border-surface-700 bg-surface-850/45 space-y-3">
            <span class="text-xs font-bold text-slate-450 uppercase tracking-wider">Параметры ATSC</span>
            
            <div>
              <label class="block text-xs text-slate-400 mb-1">Частота транспондера (МГц)</label>
              <input
                type="number"
                v-model.number="adapterForm.dvbtFreq"
                placeholder="360"
                class="w-full px-3 py-2 text-sm rounded-lg bg-surface-750 border border-surface-650 text-white placeholder-slate-550 focus:outline-none focus:border-accent font-mono"
                required
              />
            </div>
          </div>

          <!-- DVB-ASI (информация о заглушке) -->
          <div v-else-if="adapterForm.type === 'ASI'" class="p-3 rounded-lg border border-surface-700 bg-surface-850/45">
            <span class="text-xs font-bold text-slate-455 uppercase tracking-wider block mb-1">DVB-ASI тюнер</span>
            <p class="text-[11px] text-slate-400">Для тюнеров DVB-ASI дополнительные параметры частот не требуются.</p>
          </div>

          <!-- Расширенные настройки адаптера -->
          <div>
            <button
              type="button"
              @click="adapterForm.showAdvanced = !adapterForm.showAdvanced"
              class="text-xs text-accent hover:underline flex items-center gap-1 font-semibold"
            >
              {{ adapterForm.showAdvanced ? 'Скрыть' : 'Показать' }} дополнительные настройки адаптера
              <span class="text-[10px]">{{ adapterForm.showAdvanced ? '▲' : '▼' }}</span>
            </button>

            <div v-show="adapterForm.showAdvanced" class="mt-2.5 p-3 rounded-lg border border-surface-700 bg-surface-850/45 space-y-3">
              <div class="grid grid-cols-2 gap-3">
                <div>
                  <label class="block text-[10px] text-slate-400 mb-1 font-semibold uppercase">Номер устройства fe (device)</label>
                  <input
                    type="number"
                    v-model.number="adapterForm.device"
                    placeholder="0"
                    class="w-full px-2.5 py-1.5 text-xs rounded bg-surface-750 border border-surface-650 text-white"
                  />
                </div>
                <div>
                  <label class="block text-[10px] text-slate-400 mb-1 font-semibold uppercase">Модуляция</label>
                  <select
                    v-model="adapterForm.modulation"
                    class="w-full px-2.5 py-1.5 text-xs rounded bg-surface-750 border border-surface-650 text-white focus:outline-none"
                  >
                    <option value="NONE">NONE (По умолчанию S/S2)</option>
                    <option value="AUTO">AUTO (По умолчанию T/T2/C)</option>
                    <option value="QPSK">QPSK</option>
                    <option value="QAM16">QAM16</option>
                    <option value="QAM32">QAM32</option>
                    <option value="QAM64">QAM64</option>
                    <option value="QAM128">QAM128</option>
                    <option value="QAM256">QAM256</option>
                    <option value="VSB8">VSB8 (Рекомендовано ATSC)</option>
                    <option value="VSB16">VSB16</option>
                    <option value="PSK8">PSK8</option>
                    <option value="APSK16">APSK16</option>
                    <option value="APSK32">APSK32</option>
                  </select>
                </div>
              </div>

              <div class="grid grid-cols-2 gap-3">
                <div class="flex items-center gap-2 py-1">
                  <input type="checkbox" id="ctrlAdapBudget" v-model="adapterForm.budget" class="rounded bg-surface-750 text-accent" />
                  <label for="ctrlAdapBudget" class="text-xs text-slate-350 select-none font-semibold">Весь поток (budget)</label>
                </div>
                <div>
                  <label class="block text-[10px] text-slate-400 mb-1 font-semibold uppercase">Задержка CAM (сек)</label>
                  <input
                    type="number"
                    v-model.number="adapterForm.ca_pmt_delay"
                    placeholder="3"
                    class="w-full px-2.5 py-1.5 text-xs rounded bg-surface-750 border border-surface-650 text-white"
                  />
                </div>
              </div>

              <div class="grid grid-cols-2 gap-2">
                <div class="flex items-center gap-2">
                  <input type="checkbox" id="ctrlAdapRawSignal" v-model="adapterForm.raw_signal" class="rounded bg-surface-750 text-accent" />
                  <label for="ctrlAdapRawSignal" class="text-xs text-slate-350 select-none">Сигнал в dBm</label>
                </div>
                <div class="flex items-center gap-2">
                  <input type="checkbox" id="ctrlAdapLogSignal" v-model="adapterForm.log_signal" class="rounded bg-surface-750 text-accent" />
                  <label for="ctrlAdapLogSignal" class="text-xs text-slate-350 select-none">Лог сигнала каждую сек</label>
                </div>
              </div>

              <!-- Дополнительно для DVB-S/S2 -->
              <div v-if="adapterForm.type === 'S'" class="border-t border-surface-700/80 pt-2 space-y-3">
                <div class="flex items-center gap-2">
                  <input type="checkbox" id="ctrlAdapLnbSharing" v-model="adapterForm.lnb_sharing" class="rounded bg-surface-750 text-accent" />
                  <label for="ctrlAdapLnbSharing" class="text-xs text-slate-350 select-none">LNB Sharing (пассивный режим)</label>
                </div>
                <div class="grid grid-cols-2 gap-3">
                  <div>
                    <label class="block text-[10px] text-slate-400 mb-1 font-semibold uppercase">DiSEqC порт (1-4)</label>
                    <input
                      type="number"
                      v-model.number="adapterForm.diseqc"
                      placeholder="0 (DiSEqC выкл)"
                      class="w-full px-2.5 py-1.5 text-xs rounded bg-surface-750 border border-surface-650 text-white"
                    />
                  </div>
                  <div>
                    <label class="block text-[10px] text-slate-400 mb-1 font-semibold uppercase">Rolloff (DVB-S2)</label>
                    <select
                      v-model="adapterForm.rolloff"
                      class="w-full px-2.5 py-1.5 text-xs rounded bg-surface-750 border border-surface-650 text-white focus:outline-none"
                    >
                      <option value="AUTO">AUTO</option>
                      <option value="20">0.20</option>
                      <option value="25">0.25</option>
                      <option value="35">0.35</option>
                    </select>
                  </div>
                </div>
                <div class="grid grid-cols-2 gap-3">
                  <div>
                    <label class="block text-[10px] text-slate-400 mb-1 font-semibold uppercase">UniCable слот</label>
                    <input
                      type="number"
                      v-model.number="adapterForm.uni_scr"
                      placeholder="выкл"
                      class="w-full px-2.5 py-1.5 text-xs rounded bg-surface-750 border border-surface-650 text-white font-mono"
                    />
                  </div>
                  <div>
                    <label class="block text-[10px] text-slate-400 mb-1 font-semibold uppercase">UniCable частота (МГц)</label>
                    <input
                      type="number"
                      v-model.number="adapterForm.uni_frequency"
                      placeholder="выкл"
                      class="w-full px-2.5 py-1.5 text-xs rounded bg-surface-750 border border-surface-650 text-white font-mono"
                    />
                  </div>
                </div>
                <div class="grid grid-cols-2 gap-3">
                  <div class="flex items-center gap-2 py-1">
                    <input type="checkbox" id="ctrlAdapTone" v-model="adapterForm.tone" class="rounded bg-surface-750 text-accent" />
                    <label for="ctrlAdapTone" class="text-xs text-slate-350 select-none font-semibold">Тон 22 KHz (tone)</label>
                  </div>
                  <div>
                    <label class="block text-[10px] text-slate-400 mb-1 font-semibold uppercase">Stream ID (PLP)</label>
                    <input
                      type="number"
                      v-model.number="adapterForm.dvbsStreamId"
                      placeholder="AUTO"
                      class="w-full px-2.5 py-1.5 text-xs rounded bg-surface-750 border border-surface-650 text-white font-mono"
                    />
                  </div>
                </div>
              </div>

              <!-- Дополнительно для DVB-T/T2 -->
              <div v-if="adapterForm.type === 'T'" class="border-t border-surface-700/80 pt-2 space-y-3">
                <div class="grid grid-cols-2 gap-3">
                  <div>
                    <label class="block text-[10px] text-slate-400 mb-1 font-semibold uppercase">Ширина полосы (bandwidth)</label>
                    <select
                      v-model="adapterForm.bandwidth"
                      class="w-full px-2.5 py-1.5 text-xs rounded bg-surface-750 border border-surface-650 text-white focus:outline-none"
                    >
                      <option value="AUTO">AUTO</option>
                      <option value="6mhz">6 MHz</option>
                      <option value="7mhz">7 MHz</option>
                      <option value="8mhz">8 MHz</option>
                    </select>
                  </div>
                  <div>
                    <label class="block text-[10px] text-slate-400 mb-1 font-semibold uppercase">Защитный интервал (guard)</label>
                    <select
                      v-model="adapterForm.guardinterval"
                      class="w-full px-2.5 py-1.5 text-xs rounded bg-surface-750 border border-surface-650 text-white focus:outline-none"
                    >
                      <option value="AUTO">AUTO</option>
                      <option value="1/4">1/4</option>
                      <option value="1/8">1/8</option>
                      <option value="1/16">1/16</option>
                      <option value="1/32">1/32</option>
                    </select>
                  </div>
                </div>
                <div class="grid grid-cols-2 gap-3">
                  <div>
                    <label class="block text-[10px] text-slate-400 mb-1 font-semibold uppercase">Режим FFT (transmitmode)</label>
                    <select
                      v-model="adapterForm.transmitmode"
                      class="w-full px-2.5 py-1.5 text-xs rounded bg-surface-750 border border-surface-650 text-white focus:outline-none"
                    >
                      <option value="AUTO">AUTO</option>
                      <option value="2K">2K</option>
                      <option value="8K">8K</option>
                      <option value="4K">4K</option>
                      <option value="16K">16K</option>
                      <option value="32K">32K</option>
                    </select>
                  </div>
                  <div>
                    <label class="block text-[10px] text-slate-400 mb-1 font-semibold uppercase">Иерархия</label>
                    <select
                      v-model="adapterForm.hierarchy"
                      class="w-full px-2.5 py-1.5 text-xs rounded bg-surface-750 border border-surface-650 text-white focus:outline-none"
                    >
                      <option value="AUTO">AUTO</option>
                      <option value="NONE">NONE</option>
                      <option value="1">1</option>
                      <option value="2">2</option>
                      <option value="4">4</option>
                    </select>
                  </div>
                </div>
                <div>
                  <label class="block text-[10px] text-slate-400 mb-1 font-semibold uppercase">PLP Stream ID</label>
                  <input
                    type="number"
                    v-model.number="adapterForm.dvbtStreamId"
                    placeholder="AUTO"
                    class="w-full px-2.5 py-1.5 text-xs rounded bg-surface-750 border border-surface-650 text-white font-mono"
                  />
                </div>
              </div>
            </div>
          </div>

          <!-- Мониторинг -->
          <div class="flex items-center gap-2 py-1">
            <input
              type="checkbox"
              id="ctrlAdapMonitor"
              v-model="adapterForm.monitor"
              class="rounded bg-surface-750 border-surface-650 text-accent focus:ring-accent"
            />
            <label for="ctrlAdapMonitor" class="text-xs text-slate-350 select-none">Включить автоматический мониторинг</label>
          </div>

          <div class="flex justify-end gap-3 pt-4 border-t border-surface-700/60">
            <Button variant="ghost" size="sm" @click="closeAddAdapterModal">Отмена</Button>
            <Button variant="primary" size="sm" type="submit" :loading="submitting">Создать</Button>
          </div>
        </form>
      </div>
    </div>

  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import http from '@/core/api'
import Card from '@/components/ui/Card.vue'
import Button from '@/components/ui/Button.vue'

interface ChannelItem {
  instance_index: number
  instance_label: string
  name: string
  ready: boolean
  inputs: string[]
  outputs: string[]
}

interface AdapterItem {
  instance_index: number
  instance_label: string
  name: string
  adapter_id: number
  type: string
}

const instances = ref<any[]>([])
const selectedInstance = ref<number | string>('')
const loading = ref(false)
const submitting = ref(false)
const deletingItem = ref<string | null>(null)

// Списки
const channels = ref<ChannelItem[]>([])
const adapters = ref<AdapterItem[]>([])

// Модалки
const addChannelOpen = ref(false)
const addAdapterOpen = ref(false)

// Формы
const channelForm = ref({
  name: '',
  inputType: 'dvb',
  dvbAdapter: '',
  dvbPnr: 100,
  httpUrl: '',
  udpIp: '239.100.1.1',
  udpPort: 1234,
  filePath: '/opt/media/video.ts',
  fileLoop: true,
  outputType: 'http',
  outHttpPort: 8001,
  outHttpPath: '',
  outUdpIp: '239.200.1.1',
  outUdpPort: 1234,
  outFilePath: '/opt/media/record.ts',
  fileAio: false,
  monitor: true,
  
  // Расширенные настройки канала:
  enable: true,
  timeout: '' as number | string,
  map: '',
  set_pnr: '' as number | string,
  set_tsid: '' as number | string,
  http_keep_active: '' as number | string,
  service_provider: '',
  service_name: '',
  
  // Общие расширенные настройки входа (декодирование и фильтры):
  useBiss: false,
  bissKey: '',
  useCam: false,
  useSoftcam: false,
  softcamReader: '',
  passSdt: false,
  passEit: false,
  noReload: false,
  
  // Расширенные настройки входа HTTP:
  httpUa: '',
  httpTimeout: '' as number | string,
  httpBufferSize: '' as number | string,
  
  // Расширенные настройки входа UDP:
  udpInterface: '',
  
  // Расширенные настройки выхода HTTP:
  outHttpBufferSize: '' as number | string,
  outHttpBufferFill: '' as number | string,
  
  // Расширенные настройки выхода UDP:
  outUdpInterface: '',
  outUdpTtl: '' as number | string,
  
  // Флаги показа спойлеров
  showAdvancedChannel: false,
  showAdvancedInput: false,
  showAdvancedOutput: false
})

const adapterForm = ref({
  name: 'adapter_0',
  adapter: 0,
  type: 'S',
  dvbsFreq: 11605,
  dvbsPol: 'V',
  dvbsSr: 43200,
  dvbsLnb: '9750:10600:11700',
  dvbtFreq: 498,
  monitor: true,
  
  // Расширенные общие параметры адаптера:
  device: 0,
  modulation: 'NONE',
  budget: false,
  ca_pmt_delay: 3,
  raw_signal: false,
  log_signal: false,
  
  // Расширенные DVB-S/S2:
  lnb_sharing: false,
  diseqc: 0,
  tone: false,
  rolloff: '35',
  uni_scr: '' as number | string,
  uni_frequency: '' as number | string,
  dvbsStreamId: '' as number | string,
  
  // Расширенные DVB-T/T2:
  bandwidth: 'AUTO',
  guardinterval: 'AUTO',
  transmitmode: 'AUTO',
  hierarchy: 'AUTO',
  dvbtStreamId: '' as number | string,
  
  // Расширенные DVB-C:
  dvbcSr: 6900,
  dvbcModulation: 'QAM64',
  
  // Показ спойлеров
  showAdvanced: false
})

// Информация о выбранном инстансе
const selectedInstanceInfo = computed(() => {
  if (selectedInstance.value === '') return null
  return instances.value.find(i => i.index === Number(selectedInstance.value)) || null
})

// Отфильтрованные каналы и адаптеры
const currentChannels = computed(() => {
  if (selectedInstance.value === '') return []
  return channels.value.filter(c => c.instance_index === Number(selectedInstance.value))
})

const currentAdapters = computed(() => {
  if (selectedInstance.value === '') return []
  return adapters.value.filter(a => a.instance_index === Number(selectedInstance.value))
})

async function loadInstances() {
  try {
    const { data } = await http.get('/api/v1/m/astra/instances')
    instances.value = data.items || []
    
    // Если есть онлайн инстанс, выберем первый по умолчанию
    if (selectedInstance.value === '') {
      const online = instances.value.find(i => i.online)
      if (online) {
        selectedInstance.value = online.index
        loadData()
      }
    }
  } catch (err) {
    console.error('Ошибка загрузки экземпляров Astra', err)
  }
}

async function loadData() {
  if (selectedInstance.value === '') return
  loading.value = true
  try {
    const [chanRes, adapRes] = await Promise.all([
      http.get('/api/v1/m/astra/monitoring/channels'),
      http.get('/api/v1/m/astra/monitoring/adapters')
    ])
    channels.value = chanRes.data.items || []
    adapters.value = adapRes.data.items || []
  } catch (err) {
    console.error('Ошибка загрузки данных инстанса', err)
  } finally {
    loading.value = false
  }
}

function onInstanceChange() {
  loadData()
}

// Управление каналами
function openAddChannelModal() {
  channelForm.value = {
    name: '',
    inputType: 'dvb',
    dvbAdapter: currentAdapters.value.length > 0 ? currentAdapters.value[0].name : '',
    dvbPnr: 100,
    httpUrl: '',
    udpIp: '239.100.1.1',
    udpPort: 1234,
    filePath: '/opt/media/video.ts',
    fileLoop: true,
    outputType: 'http',
    outHttpPort: 8001,
    outHttpPath: '',
    outUdpIp: '239.200.1.1',
    outUdpPort: 1234,
    outFilePath: '/opt/media/record.ts',
    fileAio: false,
    monitor: true,
    
    enable: true,
    timeout: '',
    map: '',
    set_pnr: '',
    set_tsid: '',
    http_keep_active: '',
    service_provider: '',
    service_name: '',
    
    useBiss: false,
    bissKey: '',
    useCam: false,
    useSoftcam: false,
    softcamReader: '',
    passSdt: false,
    passEit: false,
    noReload: false,
    
    httpUa: '',
    httpTimeout: '',
    httpBufferSize: '',
    
    udpInterface: '',
    
    outHttpBufferSize: '',
    outHttpBufferFill: '',
    
    outUdpInterface: '',
    outUdpTtl: '',
    
    showAdvancedChannel: false,
    showAdvancedInput: false,
    showAdvancedOutput: false
  }
  addChannelOpen.value = true
}

function closeAddChannelModal() {
  addChannelOpen.value = false
}

async function submitAddChannel() {
  if (selectedInstance.value === '') return
  submitting.value = true

  // Генерация URI входа на основе полей
  let inputStr = ''
  let baseUri = ''
  
  if (channelForm.value.inputType === 'dvb') {
    if (!channelForm.value.dvbAdapter) {
      alert('Пожалуйста, выберите DVB-адаптер. Если его нет, сначала создайте его!')
      submitting.value = false
      return
    }
    baseUri = `dvb://${channelForm.value.dvbAdapter}`
  } else if (channelForm.value.inputType === 'http') {
    baseUri = channelForm.value.httpUrl.trim()
  } else if (channelForm.value.inputType === 'udp') {
    let host = channelForm.value.udpIp.trim()
    if (channelForm.value.udpInterface.trim()) {
      host = `${channelForm.value.udpInterface.trim()}@${host}`
    }
    baseUri = `udp://${host}:${channelForm.value.udpPort}`
  } else if (channelForm.value.inputType === 'file') {
    baseUri = `file://${channelForm.value.filePath.trim()}`
  }

  // Параметры хэша входа
  const h: string[] = []
  
  // PNR обязателен для DVB
  if (channelForm.value.inputType === 'dvb') {
    h.push(`pnr=${channelForm.value.dvbPnr}`)
  }
  
  // Декодирование (для любых входов)
  if (channelForm.value.useCam) {
    h.push('cam')
  }
  if (channelForm.value.useSoftcam && channelForm.value.softcamReader.trim()) {
    h.push(`cam=${channelForm.value.softcamReader.trim()}`)
  }
  if (channelForm.value.useBiss && channelForm.value.bissKey.trim()) {
    h.push(`biss=${channelForm.value.bissKey.trim()}`)
  }
  
  // Фильтры таблиц
  if (channelForm.value.passSdt) h.push('pass_sdt')
  if (channelForm.value.passEit) h.push('pass_eit')
  if (channelForm.value.noReload) h.push('no_reload')

  // Специфичные хэш-параметры входа
  if (channelForm.value.inputType === 'http') {
    if (channelForm.value.httpUa.trim()) h.push(`ua=${encodeURIComponent(channelForm.value.httpUa.trim())}`)
    if (channelForm.value.httpTimeout) h.push(`timeout=${channelForm.value.httpTimeout}`)
    if (channelForm.value.httpBufferSize) h.push(`buffer_size=${channelForm.value.httpBufferSize}`)
  } else if (channelForm.value.inputType === 'file') {
    if (channelForm.value.fileLoop) h.push('loop')
  }

  inputStr = baseUri
  if (h.length > 0) {
    inputStr += `#${h.join('&')}`
  }

  // Генерация URI выхода на основе полей
  let outputStr = ''
  if (channelForm.value.outputType === 'http') {
    let path = channelForm.value.outHttpPath.trim()
    if (!path.startsWith('/')) {
      path = '/' + path
    }
    outputStr = `http://0.0.0.0:${channelForm.value.outHttpPort}${path}`
    
    const hOut: string[] = []
    if (channelForm.value.outHttpBufferSize) hOut.push(`buffer_size=${channelForm.value.outHttpBufferSize}`)
    if (channelForm.value.outHttpBufferFill) hOut.push(`buffer_fill=${channelForm.value.outHttpBufferFill}`)
    
    if (hOut.length > 0) {
      outputStr += `#${hOut.join('&')}`
    }
  } else if (channelForm.value.outputType === 'udp') {
    let base = channelForm.value.outUdpIp.trim()
    if (channelForm.value.outUdpInterface.trim()) {
      base = `${channelForm.value.outUdpInterface.trim()}@${base}`
    }
    outputStr = `udp://${base}:${channelForm.value.outUdpPort}`
    
    const hOut: string[] = []
    if (channelForm.value.outUdpTtl) hOut.push(`ttl=${channelForm.value.outUdpTtl}`)
    
    if (hOut.length > 0) {
      outputStr += `#${hOut.join('&')}`
    }
  } else if (channelForm.value.outputType === 'file') {
    outputStr = `file://${channelForm.value.outFilePath.trim()}`
    if (channelForm.value.fileAio) {
      outputStr += '#aio'
    }
  }

  const payload: any = {
    name: channelForm.value.name,
    input: [inputStr],
    output: [outputStr],
    monitor: channelForm.value.monitor,
    enable: channelForm.value.enable
  }

  // Дополнительные параметры канала
  if (channelForm.value.timeout !== '') payload.timeout = Number(channelForm.value.timeout)
  if (channelForm.value.map.trim()) payload.map = channelForm.value.map.trim()
  if (channelForm.value.set_pnr !== '') payload.set_pnr = Number(channelForm.value.set_pnr)
  if (channelForm.value.set_tsid !== '') payload.set_tsid = Number(channelForm.value.set_tsid)
  if (channelForm.value.http_keep_active !== '') payload.http_keep_active = Number(channelForm.value.http_keep_active)
  if (channelForm.value.service_provider.trim()) payload.service_provider = channelForm.value.service_provider.trim()
  if (channelForm.value.service_name.trim()) payload.service_name = channelForm.value.service_name.trim()

  try {
    await http.post(`/api/v1/m/astra/monitoring/channels/${selectedInstance.value}/create`, payload)
    closeAddChannelModal()
    await loadData()
  } catch (err: any) {
    alert(`Ошибка создания канала: ${err?.response?.data?.detail || err.message}`)
  } finally {
    submitting.value = false
  }
}

async function deleteChannel(channelName: string) {
  if (selectedInstance.value === '') return
  if (!confirm(`Вы действительно хотите удалить ТВ-канал "${channelName}"?`)) return
  
  deletingItem.value = `channel-${channelName}`
  try {
    await http.post(`/api/v1/m/astra/monitoring/channels/${selectedInstance.value}/${channelName}/delete`)
    await loadData()
  } catch (err: any) {
    alert(`Ошибка удаления канала: ${err?.response?.data?.detail || err.message}`)
  } finally {
    deletingItem.value = null
  }
}

// Управление адаптерами
function openAddAdapterModal() {
  adapterForm.value = {
    name: `adapter_${currentAdapters.value.length}`,
    adapter: currentAdapters.value.length,
    type: 'S',
    dvbsFreq: 11605,
    dvbsPol: 'V',
    dvbsSr: 43200,
    dvbsLnb: '9750:10600:11700',
    dvbtFreq: 498,
    monitor: true,
    
    device: 0,
    modulation: 'NONE',
    budget: false,
    ca_pmt_delay: 3,
    raw_signal: false,
    log_signal: false,
    
    lnb_sharing: false,
    diseqc: 0,
    tone: false,
    rolloff: '35',
    uni_scr: '',
    uni_frequency: '',
    dvbsStreamId: '',
    
    bandwidth: 'AUTO',
    guardinterval: 'AUTO',
    transmitmode: 'AUTO',
    hierarchy: 'AUTO',
    dvbtStreamId: '',
    
    dvbcSr: 6900,
    dvbcModulation: 'QAM64',
    
    showAdvanced: false
  }
  addAdapterOpen.value = true
}

function closeAddAdapterModal() {
  addAdapterOpen.value = false
}

async function submitAddAdapter() {
  if (selectedInstance.value === '') return
  submitting.value = true

  // Генерация строки транспондера или частоты
  let tpStr = ''
  if (adapterForm.value.type === 'S') {
    tpStr = `${adapterForm.value.dvbsFreq}:${adapterForm.value.dvbsPol}:${adapterForm.value.dvbsSr}`
  } else if (adapterForm.value.type === 'T') {
    tpStr = `${adapterForm.value.dvbtFreq}`
  } else if (adapterForm.value.type === 'C') {
    tpStr = `${adapterForm.value.dvbtFreq}`
  } else if (adapterForm.value.type === 'ATSC') {
    tpStr = `${adapterForm.value.dvbtFreq}`
  }

  const payload: any = {
    name: adapterForm.value.name,
    adapter: Number(adapterForm.value.adapter),
    type: adapterForm.value.type,
    monitor: adapterForm.value.monitor,
    budget: adapterForm.value.budget,
    ca_pmt_delay: Number(adapterForm.value.ca_pmt_delay),
    raw_signal: adapterForm.value.raw_signal,
    log_signal: adapterForm.value.log_signal
  }

  if (adapterForm.value.type === 'S') {
    payload.tp = tpStr
  } else if (adapterForm.value.type === 'ASI') {
    // ASI не имеет частот
  } else {
    payload.frequency = Number(adapterForm.value.dvbtFreq)
  }

  if (Number(adapterForm.value.device) > 0) {
    payload.device = Number(adapterForm.value.device)
  }

  if (adapterForm.value.modulation !== 'NONE' && adapterForm.value.modulation !== 'AUTO') {
    payload.modulation = adapterForm.value.modulation
  } else if (adapterForm.value.type === 'ATSC' && adapterForm.value.modulation === 'NONE') {
    payload.modulation = 'VSB8'
  }

  if (adapterForm.value.type === 'S') {
    payload.lnb = adapterForm.value.dvbsLnb
    payload.lnb_sharing = adapterForm.value.lnb_sharing
    payload.tone = adapterForm.value.tone
    if (Number(adapterForm.value.diseqc) > 0) payload.diseqc = Number(adapterForm.value.diseqc)
    if (adapterForm.value.rolloff !== 'AUTO') payload.rolloff = adapterForm.value.rolloff
    if (adapterForm.value.uni_scr !== '') payload.uni_scr = Number(adapterForm.value.uni_scr)
    if (adapterForm.value.uni_frequency !== '') payload.uni_frequency = Number(adapterForm.value.uni_frequency)
    if (adapterForm.value.dvbsStreamId !== '') payload.stream_id = Number(adapterForm.value.dvbsStreamId)
  } else if (adapterForm.value.type === 'T') {
    if (adapterForm.value.bandwidth !== 'AUTO') payload.bandwidth = adapterForm.value.bandwidth
    if (adapterForm.value.guardinterval !== 'AUTO') payload.guardinterval = adapterForm.value.guardinterval
    if (adapterForm.value.transmitmode !== 'AUTO') payload.transmitmode = adapterForm.value.transmitmode
    if (adapterForm.value.hierarchy !== 'AUTO') payload.hierarchy = adapterForm.value.hierarchy
    if (adapterForm.value.dvbtStreamId !== '') payload.stream_id = Number(adapterForm.value.dvbtStreamId)
  } else if (adapterForm.value.type === 'C') {
    payload.symbolrate = Number(adapterForm.value.dvbcSr)
    payload.modulation = adapterForm.value.dvbcModulation
  }

  try {
    await http.post(`/api/v1/m/astra/monitoring/adapters/${selectedInstance.value}/create`, payload)
    closeAddAdapterModal()
    await loadData()
  } catch (err: any) {
    alert(`Ошибка создания адаптера: ${err?.response?.data?.detail || err.message}`)
  } finally {
    submitting.value = false
  }
}

async function deleteAdapter(adapterName: string) {
  if (selectedInstance.value === '') return
  if (!confirm(`Вы действительно хотите удалить DVB-адаптер "${adapterName}"?`)) return

  deletingItem.value = `adapter-${adapterName}`
  try {
    await http.delete(`/api/v1/m/astra/monitoring/adapters/${selectedInstance.value}/${adapterName}`)
    await loadData()
  } catch (err: any) {
    alert(`Ошибка удаления адаптера: ${err?.response?.data?.detail || err.message}`)
  } finally {
    deletingItem.value = null
  }
}

onMounted(() => {
  loadInstances()
})
</script>
