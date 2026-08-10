/**
 * Аудио-синтезатор звуковых сигналов на основе Web Audio API.
 * Не требует загрузки внешних аудиофайлов или библиотек.
 */

let sharedAudioCtx: AudioContext | null = null

export function getAudioContext(): AudioContext | null {
  if (typeof window === 'undefined') return null
  if (!sharedAudioCtx) {
    const AudioContextClass = window.AudioContext || (window as any).webkitAudioContext
    if (AudioContextClass) {
      sharedAudioCtx = new AudioContextClass()
    }
  }
  if (sharedAudioCtx && sharedAudioCtx.state === 'suspended') {
    sharedAudioCtx.resume().catch(() => {})
  }
  return sharedAudioCtx
}

export function unlockAudioContext(): void {
  try {
    const ctx = sharedAudioCtx || getAudioContext()
    if (ctx && ctx.state === 'suspended') {
      ctx.resume().catch(() => {})
    }
  } catch {
    // Игнорируем ошибки автоплея браузера
  }
}

export interface SoundPreset {
  id: string
  labelKey: string
  defaultLabel: string
}

export const SOUND_PRESETS: SoundPreset[] = [
  { id: 'chime', labelKey: 'soundChime', defaultLabel: 'Мягкий перезвон (Chime)' },
  { id: 'success', labelKey: 'soundSuccess', defaultLabel: 'Мажорный аккорд (Success)' },
  { id: 'warning', labelKey: 'soundWarning', defaultLabel: 'Двойной сигнал (Warning)' },
  { id: 'error', labelKey: 'soundError', defaultLabel: 'Тревожный сигнал (Error)' },
  { id: 'bell', labelKey: 'soundBell', defaultLabel: 'Колокольчик (Bell)' },
  { id: 'subtle', labelKey: 'soundSubtle', defaultLabel: 'Тихий клик (Subtle)' },
  { id: 'pulse', labelKey: 'soundPulse', defaultLabel: 'Импульсный тон (Pulse)' },
  { id: 'none', labelKey: 'soundNone', defaultLabel: 'Без звука (Mute)' },
]

export const DEFAULT_SEVERITY_SOUNDS: Record<string, string> = {
  info: 'chime',
  success: 'success',
  warning: 'warning',
  error: 'error',
}

export function playPresetSound(presetId: string, customCtx?: AudioContext | null): void {
  if (!presetId || presetId === 'none') return

  try {
    const ctx = customCtx || getAudioContext()
    if (!ctx) return

    if (ctx.state === 'suspended') {
      ctx.resume().then(() => {
        if (ctx.state === 'running') runPresetSynthesis(ctx, presetId)
      }).catch(() => {})
    } else if (ctx.state === 'running') {
      runPresetSynthesis(ctx, presetId)
    }
  } catch {
    // Ошибки проигрывания игнорируются
  }
}

function runPresetSynthesis(ctx: AudioContext, presetId: string): void {
  const now = ctx.currentTime

  switch (presetId) {
    case 'chime': {
      // Двухтональный мягкий свип (587.33Hz D5 -> 880Hz A5)
      const osc = ctx.createOscillator()
      const gain = ctx.createGain()
      osc.type = 'sine'
      osc.frequency.setValueAtTime(587.33, now)
      osc.frequency.exponentialRampToValueAtTime(880, now + 0.15)
      gain.gain.setValueAtTime(0.15, now)
      gain.gain.exponentialRampToValueAtTime(0.001, now + 0.18)
      osc.connect(gain)
      gain.connect(ctx.destination)
      osc.start(now)
      osc.stop(now + 0.18)
      break
    }

    case 'success': {
      // Быстрый мажорный трезвучный арпеджио C5-E5-G5 (523Hz, 659Hz, 784Hz)
      const freqs = [523.25, 659.25, 783.99]
      freqs.forEach((freq, idx) => {
        const osc = ctx.createOscillator()
        const gain = ctx.createGain()
        const startTime = now + idx * 0.06
        osc.type = 'sine'
        osc.frequency.setValueAtTime(freq, startTime)
        gain.gain.setValueAtTime(0.12, startTime)
        gain.gain.exponentialRampToValueAtTime(0.001, startTime + 0.15)
        osc.connect(gain)
        gain.connect(ctx.destination)
        osc.start(startTime)
        osc.stop(startTime + 0.15)
      })
      break
    }

    case 'warning': {
      // Двойной пульсирующий предупреждающий сигнал (440Hz A4)
      [0, 0.1].forEach((delay) => {
        const osc = ctx.createOscillator()
        const gain = ctx.createGain()
        const startTime = now + delay
        osc.type = 'triangle'
        osc.frequency.setValueAtTime(440, startTime)
        gain.gain.setValueAtTime(0.18, startTime)
        gain.gain.exponentialRampToValueAtTime(0.001, startTime + 0.07)
        osc.connect(gain)
        gain.connect(ctx.destination)
        osc.start(startTime)
        osc.stop(startTime + 0.07)
      })
      break
    }

    case 'error': {
      // Тревожный убывающий сигнал высокой частоты (880Hz -> 440Hz saw/triangle)
      [0, 0.12].forEach((delay, idx) => {
        const osc = ctx.createOscillator()
        const gain = ctx.createGain()
        const startTime = now + delay
        osc.type = 'sawtooth'
        osc.frequency.setValueAtTime(880 - idx * 120, startTime)
        osc.frequency.exponentialRampToValueAtTime(440 - idx * 60, startTime + 0.1)
        gain.gain.setValueAtTime(0.15, startTime)
        gain.gain.exponentialRampToValueAtTime(0.001, startTime + 0.1)
        osc.connect(gain)
        gain.connect(ctx.destination)
        osc.start(startTime)
        osc.stop(startTime + 0.1)
      })
      break
    }

    case 'bell': {
      // Колокольчик с гармоникой (835Hz)
      const osc1 = ctx.createOscillator()
      const osc2 = ctx.createOscillator()
      const gain = ctx.createGain()
      osc1.type = 'sine'
      osc2.type = 'sine'
      osc1.frequency.setValueAtTime(835, now)
      osc2.frequency.setValueAtTime(1670, now)
      gain.gain.setValueAtTime(0.12, now)
      gain.gain.exponentialRampToValueAtTime(0.001, now + 0.3)
      osc1.connect(gain)
      osc2.connect(gain)
      gain.connect(ctx.destination)
      osc1.start(now)
      osc2.start(now)
      osc1.stop(now + 0.3)
      osc2.stop(now + 0.3)
      break
    }

    case 'subtle': {
      // Низкий мягкий клик (350Hz -> 200Hz)
      const osc = ctx.createOscillator()
      const gain = ctx.createGain()
      osc.type = 'sine'
      osc.frequency.setValueAtTime(350, now)
      osc.frequency.exponentialRampToValueAtTime(200, now + 0.05)
      gain.gain.setValueAtTime(0.08, now)
      gain.gain.exponentialRampToValueAtTime(0.001, now + 0.05)
      osc.connect(gain)
      gain.connect(ctx.destination)
      osc.start(now)
      osc.stop(now + 0.05)
      break
    }

    case 'pulse': {
      // Тройной динамический импульс (650Hz)
      [0, 0.08, 0.16].forEach((delay) => {
        const osc = ctx.createOscillator()
        const gain = ctx.createGain()
        const startTime = now + delay
        osc.type = 'sine'
        osc.frequency.setValueAtTime(650, startTime)
        gain.gain.setValueAtTime(0.1, startTime)
        gain.gain.exponentialRampToValueAtTime(0.001, startTime + 0.05)
        osc.connect(gain)
        gain.connect(ctx.destination)
        osc.start(startTime)
        osc.stop(startTime + 0.05)
      })
      break
    }

    default: {
      // Резервный chime
      const osc = ctx.createOscillator()
      const gain = ctx.createGain()
      osc.type = 'sine'
      osc.frequency.setValueAtTime(587.33, now)
      osc.frequency.exponentialRampToValueAtTime(880, now + 0.15)
      gain.gain.setValueAtTime(0.15, now)
      gain.gain.exponentialRampToValueAtTime(0.001, now + 0.15)
      osc.connect(gain)
      gain.connect(ctx.destination)
      osc.start(now)
      osc.stop(now + 0.15)
      break
    }
  }
}
