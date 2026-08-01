<template>
  <div class="min-h-full p-6 flex gap-6 w-full animate-fade-in text-on-surface">
    <!-- Wiki Side Navigation Bar (Standalone) -->
    <aside class="w-64 shrink-0 hidden md:flex flex-col gap-4 border-r border-outline-variant/40 pr-4">
      <!-- Search Box -->
      <div class="relative">
        <span class="material-symbols-outlined absolute left-3 top-2.5 text-sm text-on-surface-variant">search</span>
        <input
          v-model="searchQuery"
          type="text"
          placeholder="Поиск по вики..."
          class="w-full bg-surface-container-high border border-outline-variant/60 rounded-xl pl-9 pr-3 py-2 text-xs text-on-surface focus:outline-none focus:border-primary"
        />
      </div>

      <!-- Wiki Documents & Sections -->
      <div class="space-y-4 overflow-y-auto">
        <!-- Main Category: Developer Guides -->
        <div class="space-y-2">
          <div class="flex items-center gap-2 px-2 font-mono text-[10px] text-on-surface-variant uppercase tracking-widest font-bold opacity-80">
            <span class="material-symbols-outlined text-xs text-primary">menu_book</span>
            <span>База знаний</span>
          </div>

          <!-- Active Document Pill -->
          <div class="px-3 py-2 rounded-xl bg-primary/10 border border-primary/30 text-primary font-bold text-xs flex items-center gap-2 shadow-glow">
            <span class="material-symbols-outlined text-base">extension</span>
            <span class="truncate">Создание модулей</span>
          </div>
        </div>

        <!-- Section Navigation inside active Document -->
        <div v-if="sections.length > 0" class="space-y-1 pl-2 border-l border-outline-variant/40">
          <div class="px-2 py-1 font-mono text-[9px] text-on-surface-variant uppercase tracking-wider font-bold">
            Оглавление статьи
          </div>

          <button
            v-for="sec in filteredSections"
            :key="sec.id"
            @click="scrollToSection(sec.id)"
            class="w-full flex items-center gap-2 px-2.5 py-1.5 rounded-lg text-xs text-left transition-colors border"
            :class="activeSection === sec.id
              ? 'bg-surface-container-high border-outline-variant text-primary font-bold border-l-2 !border-l-primary'
              : 'text-on-surface-variant border-transparent hover:bg-surface-variant/40 hover:text-on-surface'"
          >
            <span class="material-symbols-outlined text-sm flex-shrink-0">{{ sec.icon }}</span>
            <span class="truncate text-[11px]">{{ sec.title }}</span>
          </button>
        </div>
      </div>
    </aside>

    <!-- Main Wiki Content Area -->
    <div class="flex-1 flex flex-col gap-6 w-full pb-12 min-w-0">
      <!-- Top Header -->
      <div class="flex items-center justify-between border-b border-outline-variant/50 pb-4">
        <div>
          <div class="flex items-center gap-2 text-xs font-mono text-primary font-semibold mb-1 uppercase tracking-wider">
            <span class="material-symbols-outlined text-sm">auto_stories</span>
            <span>Вики / Документация</span>
          </div>
          <h1 class="font-bold text-2xl text-on-surface">Руководство по модульной системе NMS</h1>
          <p class="text-xs text-on-surface-variant mt-1">
            Официальное справочное руководство по архитектуре модулей, разрешениям, настройкам, локализации и виджетам
          </p>
        </div>

        <div class="flex items-center gap-3">
          <button
            @click="loadDoc"
            :disabled="loading"
            class="bg-surface-container-high hover:bg-surface-variant text-on-surface px-3 py-1.5 rounded-lg text-xs font-semibold transition-colors flex items-center gap-1.5 border border-outline-variant"
            title="Перезагрузить статью"
          >
            <span class="material-symbols-outlined text-sm" :class="{ 'animate-spin': loading }">refresh</span>
            Обновить
          </button>
        </div>
      </div>

      <!-- Quick Nav Pills (Mobile & Desktop) -->
      <div class="flex flex-wrap gap-2">
        <button
          v-for="sec in sections"
          :key="sec.id"
          @click="scrollToSection(sec.id)"
          class="px-3 py-1.5 rounded-lg text-xs font-semibold border transition-all flex items-center gap-1.5"
          :class="activeSection === sec.id
            ? 'bg-primary text-on-primary border-primary shadow-glow'
            : 'bg-surface-container-low text-on-surface-variant border-outline-variant/40 hover:bg-surface-container-high hover:text-on-surface'"
        >
          <span class="material-symbols-outlined text-sm">{{ sec.icon }}</span>
          <span>{{ sec.title }}</span>
        </button>
      </div>

      <!-- Loading / Error State -->
      <div v-if="loading" class="flex items-center justify-center py-20 text-on-surface-variant gap-3">
        <span class="material-symbols-outlined animate-spin text-primary text-2xl">progress_activity</span>
        <span class="text-sm font-medium">Загрузка статьи вики...</span>
      </div>

      <div v-else-if="error" class="p-4 rounded-xl bg-error/10 border border-error/30 text-error text-xs space-y-2">
        <div class="flex items-center gap-2 font-bold">
          <span class="material-symbols-outlined">error</span>
          <span>Не удалось загрузить документацию</span>
        </div>
        <p>{{ error }}</p>
      </div>

      <!-- Article Rendered Container -->
      <div v-else class="bg-surface-container-low border border-outline-variant rounded-xl p-6 shadow-glow space-y-8 max-w-none font-sans">
        <div v-for="sec in filteredSections" :key="sec.id" :id="sec.id" class="space-y-4 scroll-mt-6">
          <div class="flex items-center gap-2 border-b border-outline-variant/40 pb-2">
            <span class="material-symbols-outlined text-primary text-xl">{{ sec.icon }}</span>
            <h2 class="text-lg font-bold text-on-surface">{{ sec.title }}</h2>
          </div>

          <div class="doc-body text-sm leading-relaxed text-on-surface-variant space-y-3" v-html="sec.html" />
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useI18n } from '@/core/i18n'
import { apiFetchModuleGuideDoc } from '@/core/api'

const { t } = useI18n()

const loading = ref(false)
const error = ref<string | null>(null)
const docContent = ref('')
const searchQuery = ref('')
const activeSection = ref('')

interface DocSection {
  id: string
  title: string
  icon: string
  raw: string
  html: string
}

const sections = ref<DocSection[]>([])

const filteredSections = computed(() => {
  if (!searchQuery.value.trim()) return sections.value
  const q = searchQuery.value.toLowerCase()
  return sections.value.filter(
    (s) => s.title.toLowerCase().includes(q) || s.raw.toLowerCase().includes(q)
  )
})

function escapeHtml(str: string): string {
  return str
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
}

function parseMarkdownToSections(md: string): DocSection[] {
  const sectionIcons: Record<string, string> = {
    'структура': 'folder_zip',
    'создание': 'extension',
    'разрешения': 'lock',
    'настройки': 'settings',
    'локализация': 'translate',
    'виджеты': 'widgets',
    'чеклист': 'fact_check',
  }

  const rawSections = md.split(/^##\s+/m)
  const result: DocSection[] = []

  rawSections.forEach((secText, idx) => {
    if (!secText.trim()) return
    const lines = secText.trim().split('\n')
    const headerLine = lines[0].replace(/^[\d\.\s#]+/, '').trim()
    const bodyLines = lines.slice(1).join('\n')

    const secId = `doc-sec-${idx}`
    const lowerTitle = headerLine.toLowerCase()

    let icon = 'article'
    for (const [key, ic] of Object.entries(sectionIcons)) {
      if (lowerTitle.includes(key)) {
        icon = ic
        break
      }
    }

    const html = convertMarkdownSnippetToHtml(bodyLines)

    result.push({
      id: secId,
      title: headerLine || 'Раздел',
      icon,
      raw: secText,
      html,
    })
  })

  return result
}

function convertMarkdownSnippetToHtml(md: string): string {
  let html = md

  // Code blocks ```yaml ... ```
  html = html.replace(/```([a-z]*)\n([\s\S]*?)```/g, (_match, lang, code) => {
    const safeCode = escapeHtml(code.trim())
    return `
      <div class="my-3 rounded-lg bg-surface-container-highest border border-outline-variant/60 overflow-hidden font-mono text-xs">
        <div class="px-3 py-1 bg-surface-variant/80 border-b border-outline-variant/40 flex items-center justify-between text-[10px] text-on-surface-variant font-bold uppercase">
          <span>${lang || 'code'}</span>
        </div>
        <pre class="p-3 overflow-x-auto text-primary-bright font-mono text-[11px] leading-snug"><code>${safeCode}</code></pre>
      </div>
    `
  })

  // Inline code `code`
  html = html.replace(/`([^`]+)`/g, (_m, c) => `<code class="px-1.5 py-0.5 rounded bg-surface-container-high border border-outline-variant/40 font-mono text-xs text-primary">${escapeHtml(c)}</code>`)

  // Important / Alert blocks > [!IMPORTANT]
  html = html.replace(/^>\s*\[!(IMPORTANT|NOTE|WARNING)\]\s*\n([\s\S]*?)(?=\n\n|\n#|$)/gm, (_m, type, content) => {
    const borderColor = type === 'IMPORTANT' ? 'border-primary' : type === 'WARNING' ? 'border-warning' : 'border-secondary'
    const bgColor = type === 'IMPORTANT' ? 'bg-primary/10' : type === 'WARNING' ? 'bg-warning/10' : 'bg-secondary/10'
    const icon = type === 'IMPORTANT' ? 'priority_high' : type === 'WARNING' ? 'warning' : 'info'
    return `
      <div class="my-3 p-3 rounded-lg border-l-4 ${borderColor} ${bgColor} flex items-start gap-2.5 text-xs text-on-surface">
        <span class="material-symbols-outlined text-sm flex-shrink-0 mt-0.5">${icon}</span>
        <div>${content.replace(/^>\s*/gm, '').trim()}</div>
      </div>
    `
  })

  // Headings ###
  html = html.replace(/^###\s+(.*$)/gm, '<h3 class="text-sm font-bold text-on-surface mt-4 mb-2">$1</h3>')

  // Lists - or *
  html = html.replace(/^\s*[-*]\s+(.*$)/gm, '<li class="ml-4 list-disc text-xs text-on-surface-variant">$1</li>')

  // Paragraphs
  html = html.replace(/\n\n/g, '<br/><br/>')

  return html
}

function scrollToSection(id: string) {
  activeSection.value = id
  const el = document.getElementById(id)
  if (el) {
    el.scrollIntoView({ behavior: 'smooth' })
  }
}

async function loadDoc() {
  loading.value = true
  error.value = null
  try {
    const res = await apiFetchModuleGuideDoc()
    docContent.value = res.content
    sections.value = parseMarkdownToSections(res.content)
    if (sections.value.length > 0) {
      activeSection.value = sections.value[0].id
    }
  } catch (err: any) {
    console.error('Error fetching module guide doc:', err)
    error.value = err?.response?.data?.detail || err?.message || 'Не удалось загрузить файл документации'
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  loadDoc()
})
</script>

<style scoped>
.doc-body :deep(h3) {
  color: var(--color-on-surface);
  font-weight: 700;
}
.doc-body :deep(ul) {
  margin-top: 0.5rem;
  margin-bottom: 0.5rem;
}
</style>
