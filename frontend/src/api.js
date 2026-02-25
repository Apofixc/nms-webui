const api = async (path, opts = {}) => {
  const url = path.startsWith('/') ? path : '/' + path
  const method = (opts.method || 'GET').toUpperCase()
  const res = await fetch(url, {
    method,
    headers: { 'Content-Type': 'application/json', ...opts.headers },
    ...opts,
  })
  const text = await res.text()
  if (!res.ok) throw new Error(text || res.statusText)
  if (!text) return null
  try {
    return JSON.parse(text)
  } catch {
    return text
  }
}

export default {
  instances: () => api('/api/instances'),
  instancesStatus: () => api('/api/instances/status'),
  systemInfo: () => api('/api/system/info'),
  clearStatusEvents: () => api('/api/instances/status/events', { method: 'DELETE' }),
  removeStatusEvent: (index) => api(`/api/instances/status/events/${index}`, { method: 'DELETE' }),
  setCheckInterval: (seconds) => api('/api/settings/check-interval', { method: 'PATCH', body: JSON.stringify({ seconds }) }),
  instanceCreate: (body) => api('/api/instances', { method: 'POST', body: JSON.stringify(body) }),
  instanceDelete: (id) => api(`/api/instances/${id}`, { method: 'DELETE' }),
  instanceScan: (body) => api('/api/instances/scan', { method: 'POST', body: JSON.stringify(body) }),
  instanceHealth: (id) => api(`/api/instances/${id}/health`),
  instanceMonitors: (id) => api(`/api/instances/${id}/monitors`),
  instanceMonitorsStatus: (id) => api(`/api/instances/${id}/monitors/status`),
  instanceSubscribers: (id) => api(`/api/instances/${id}/subscribers`),
  instanceDvbAdapters: (id) => api(`/api/instances/${id}/dvb/adapters`),
  instanceSystemHostname: (id) => api(`/api/instances/${id}/system/network/hostname`),
  instanceSystemInterfaces: (id) => api(`/api/instances/${id}/system/network/interfaces`),
  instanceSystemReload: (id, delay) => api(`/api/instances/${id}/system/reload`, { method: 'POST', body: JSON.stringify(delay != null ? { delay } : {}) }),
  instanceSystemExit: (id, delay) => api(`/api/instances/${id}/system/exit`, { method: 'POST', body: JSON.stringify(delay != null ? { delay } : {}) }),
  instanceSystemClearCache: (id) => api(`/api/instances/${id}/system/clear-cache`, { method: 'POST' }),
  instanceUtilsInfo: (id) => api(`/api/instances/${id}/utils/info`),
  aggregateHealth: () => api('/api/aggregate/health'),
  aggregateChannels: () => api('/api/aggregate/channels'),
  aggregateChannelsStats: () => api('/api/aggregate/channels/stats'),
  channelKill: (instanceId, name, reboot = false) =>
    api(`/api/instances/${instanceId}/channels/kill?name=${encodeURIComponent(name)}&reboot=${reboot}`, { method: 'DELETE' }),
  channelInputs: (instanceId, name) =>
    api(`/api/instances/${instanceId}/channels/inputs?name=${encodeURIComponent(name)}`),
  streamKill: (instanceId, name, reboot = false) =>
    api(`/api/instances/${instanceId}/streams/kill?name=${encodeURIComponent(name)}&reboot=${reboot}`, { method: 'DELETE' }),
  /** URL скриншота канала (GET возвращает image/jpeg) */
  channelPreviewUrl: (instanceId, name) =>
    `/api/instances/${instanceId}/channels/preview?name=${encodeURIComponent(name)}`,
  /** Запустить один цикл обновления превью в кэше (при заходе на вкладку Каналы). { started, reason? } */
  channelsPreviewRefreshStart: () =>
    api('/api/channels/preview-refresh/start', { method: 'POST' }),
  /** Статус обновления превью. { running, done_at? } */
  channelsPreviewRefreshStatus: () =>
    api('/api/channels/preview-refresh/status'),
  /** Анализ потока канала (TSDuck). Возвращает { ok, output, url } */
  channelAnalyze: (instanceId, name) =>
    api(`/api/instances/${instanceId}/channels/analyze?name=${encodeURIComponent(name)}`),
  /** Запуск сессии просмотра. body: { url } или { instance_id, channel_name }. Возвращает { playback_url, session_id } */
  streamPlaybackStart: (body) =>
    api('/api/streams/playback', { method: 'POST', body: JSON.stringify(body) }),
  streamPlaybackStop: (sessionId) =>
    api(`/api/streams/playback/${sessionId}`, { method: 'DELETE' }),
  /** Настройки WebUI: бэкенды превью и воспроизведения */
  settingsGet: () => api('/api/settings'),
  settingsPut: (body) => api('/api/settings', { method: 'PUT', body: JSON.stringify(body) }),
  /** Реестр модулей */
  modulesGet: (withSettings = false, onlyEnabled = false) =>
    api(`/api/modules?with_settings=${withSettings}&only_enabled=${onlyEnabled}`),
  moduleSetEnabled: (moduleId, enabled) =>
    api(`/api/modules/${moduleId}/enabled`, { method: 'PUT', body: JSON.stringify({ enabled }) }),
}
