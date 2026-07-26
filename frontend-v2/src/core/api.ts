import axios from 'axios'

const http = axios.create({
  baseURL: '/',
  headers: { 'Content-Type': 'application/json' },
  timeout: 10000,
})

export async function fetchModules(withSettings = false, onlyEnabled = false) {
  try {
    const { data } = await http.get('/api/modules', {
      params: { with_settings: withSettings, only_enabled: onlyEnabled },
    })
    return data
  } catch (e) {
    return { items: [] }
  }
}

export async function fetchLoadedModules() {
  try {
    const { data } = await http.get('/api/modules/loaded')
    return data
  } catch (e) {
    return { items: [] }
  }
}

export async function fetchAstraSummary() {
  try {
    const { data } = await http.get('/api/v1/m/astra/monitoring/summary')
    return data
  } catch (e) {
    return null
  }
}

export async function fetchAstraInstances() {
  try {
    const { data } = await http.get('/api/v1/m/astra/instances')
    return data
  } catch (e) {
    return { items: [] }
  }
}

export default http
