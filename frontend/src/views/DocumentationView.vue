<template>
  <div class="h-full p-6 flex gap-6 w-full animate-fade-in text-on-surface overflow-hidden">
    <!-- Wiki Side Navigation Bar (Fixed) -->
    <aside class="w-72 shrink-0 hidden md:flex flex-col gap-4 border-r border-outline-variant/40 pr-4 h-full overflow-hidden">
      <!-- Search Box -->
      <div class="relative shrink-0">
        <span class="material-symbols-outlined absolute left-3 top-2.5 text-sm text-on-surface-variant">search</span>
        <input
          v-model="searchQuery"
          type="text"
          :placeholder="t('searchWiki')"
          class="w-full bg-surface-container-high border border-outline-variant/60 rounded-xl pl-9 pr-3 py-2 text-xs text-on-surface focus:outline-none focus:border-primary"
        />
      </div>

      <!-- Wiki Navigation Tree -->
      <div class="space-y-4 overflow-y-auto flex-1 pr-1">
        <div v-for="cat in filteredCategories" :key="cat.id" class="space-y-1.5">
          <div class="flex items-center gap-2 px-2 font-mono text-[11px] text-on-surface-variant uppercase tracking-wider font-bold opacity-90">
            <span class="material-symbols-outlined text-sm text-primary">{{ cat.icon }}</span>
            <span>{{ getCategoryTitle(cat) }}</span>
          </div>

          <div class="space-y-1 pl-1">
            <button
              v-for="art in cat.articles"
              :key="art.path"
              @click="selectArticle(art)"
              class="w-full flex items-center gap-2 px-2.5 py-1.5 rounded-xl text-xs text-left transition-all border"
              :class="currentArticlePath === art.path
                ? 'bg-primary/10 border-primary/40 text-primary font-bold shadow-glow'
                : 'text-on-surface-variant border-transparent hover:bg-surface-container-high hover:text-on-surface'"
            >
              <span class="material-symbols-outlined text-xs flex-shrink-0">article</span>
              <span class="truncate text-[11px]">{{ getArticleTitle(art) }}</span>
            </button>
          </div>
        </div>
      </div>
    </aside>

    <!-- Main Wiki Content Area -->
    <div class="flex-1 flex flex-col gap-4 w-full h-full min-w-0 overflow-hidden">
      <!-- Top Header -->
      <div class="flex items-center justify-between border-b border-outline-variant/50 pb-3 shrink-0">
        <div>
          <div class="flex items-center gap-2 text-xs font-mono text-primary font-semibold mb-1 uppercase tracking-wider">
            <span class="material-symbols-outlined text-sm">auto_stories</span>
            <span>{{ t('wikiTitle') }} / {{ displayArticleTitle }}</span>
          </div>
          <h1 class="font-bold text-2xl text-on-surface">{{ displayArticleTitle }}</h1>
          <p class="text-xs text-on-surface-variant mt-1">
            {{ t('wikiDesc') }}
          </p>
        </div>

        <div class="flex items-center gap-3">
          <button
            @click="reloadCurrentArticle"
            :disabled="loading"
            class="bg-surface-container-high hover:bg-surface-variant text-on-surface px-3 py-1.5 rounded-lg text-xs font-semibold transition-colors flex items-center gap-1.5 border border-outline-variant"
            :title="t('widgetRefresh')"
          >
            <span class="material-symbols-outlined text-sm" :class="{ 'animate-spin': loading }">refresh</span>
            {{ t('widgetRefresh') }}
          </button>
        </div>
      </div>

      <!-- Quick Nav Pills for Article Sections -->
      <div v-if="sections.length > 0" class="flex flex-wrap gap-2 shrink-0">
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
      <div v-if="loading" class="flex-1 flex items-center justify-center py-20 text-on-surface-variant gap-3">
        <span class="material-symbols-outlined animate-spin text-primary text-2xl">progress_activity</span>
        <span class="text-sm font-medium">{{ t('wikiLoading') }}</span>
      </div>

      <div v-else-if="error" class="p-4 rounded-xl bg-error/10 border border-error/30 text-error text-xs space-y-2 shrink-0">
        <div class="flex items-center gap-2 font-bold">
          <span class="material-symbols-outlined">error</span>
          <span>{{ t('wikiError') }}</span>
        </div>
        <p>{{ error }}</p>
      </div>

      <!-- Article Rendered Container -->
      <div v-else class="flex-1 min-h-0 overflow-y-auto bg-surface-container-low border border-outline-variant rounded-xl p-6 shadow-glow space-y-8 max-w-none font-sans">
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
import { ref, computed, watch, onMounted, nextTick } from 'vue'
import mermaid from 'mermaid'
import { useI18n, currentLang, translations } from '@/core/i18n'
import { apiFetchWikiTree, apiFetchWikiArticle, type WikiCategoryItem, type WikiArticleItem } from '@/core/api'

mermaid.initialize({
  startOnLoad: false,
  theme: 'dark',
  securityLevel: 'loose',
})

const { t } = useI18n()

const loading = ref(false)
const error = ref<string | null>(null)
const searchQuery = ref('')
const activeSection = ref('')

const categories = ref<WikiCategoryItem[]>([])
const currentArticlePath = ref<string>('module-guide.md')
const currentArticleTitle = ref<string>('')

interface DocSection {
  id: string
  title: string
  icon: string
  raw: string
  html: string
}

const sections = ref<DocSection[]>([])

const categoryTitleKeys: Record<string, string> = {
  '01-overview': 'wikiCat_overview',
  '02-module-development': 'wikiCat_module_dev',
  '03-widgets-and-ui': 'wikiCat_widgets_ui',
  '04-backend-api': 'wikiCat_backend_api',
  '05-ops-and-deployment': 'wikiCat_ops_deploy',
  '06-troubleshooting': 'wikiCat_troubleshooting',
}

function getCategoryTitle(cat: WikiCategoryItem): string {
  const key = categoryTitleKeys[cat.id]
  return key ? t(key) : cat.title
}

function getArticleTitle(art: WikiArticleItem): string {
  if (art.path === 'module-guide.md') {
    return t('wikiModuleGuideTitle')
  }
  return art.title
}

const displayArticleTitle = computed(() => {
  if (currentArticlePath.value === 'module-guide.md') {
    return t('wikiModuleGuideTitle')
  }
  return currentArticleTitle.value
})

const filteredCategories = computed(() => {
  if (!searchQuery.value.trim()) return categories.value
  const q = searchQuery.value.toLowerCase()
  return categories.value
    .map((cat) => {
      const catTitle = getCategoryTitle(cat)
      const matchedArticles = cat.articles.filter((a) => {
        const artTitle = getArticleTitle(a)
        return artTitle.toLowerCase().includes(q) || a.path.toLowerCase().includes(q)
      })
      if (catTitle.toLowerCase().includes(q)) {
        return cat
      }
      return {
        ...cat,
        articles: matchedArticles,
      }
    })
    .filter((cat) => cat.articles.length > 0)
})

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

function getIconForTitle(lowerTitle: string): string {
  for (const langDict of Object.values(translations)) {
    const iconMap = (langDict as any).docIconKeywords
    if (!iconMap) continue
    for (const [icon, keywords] of Object.entries(iconMap)) {
      if (Array.isArray(keywords) && keywords.some((kw: string) => lowerTitle.includes(kw.toLowerCase()))) {
        return icon
      }
    }
  }
  return 'article'
}

function parseMarkdownToSections(md: string): DocSection[] {
  const rawSections = md.split(/^##\s+/m)
  const result: DocSection[] = []

  rawSections.forEach((secText, idx) => {
    if (!secText.trim()) return
    const lines = secText.trim().split('\n')
    let headerLine = lines[0].replace(/^[\d\.\s#]+/, '').trim()
    const bodyLines = lines.slice(1).join('\n')

    let icon = 'article'

    // 1. Explicit directive in header line: [icon:name] or :name:
    const iconMatch = headerLine.match(/\[icon:([a-z0-9_-]+)\]|:([a-z0-9_-]+):/i)
    if (iconMatch) {
      icon = (iconMatch[1] || iconMatch[2]).toLowerCase()
      headerLine = headerLine.replace(/\[icon:[a-z0-9_-]+\]|:[a-z0-9_-]+:/i, '').trim()
    } else {
      // 2. Lookup keywords dynamically across registered i18n locales
      icon = getIconForTitle(headerLine.toLowerCase())
    }

    const secId = `doc-sec-${idx}`
    const html = convertMarkdownSnippetToHtml(bodyLines || secText)

    result.push({
      id: secId,
      title: headerLine || t('docSectionDefault'),
      icon,
      raw: secText,
      html,
    })
  })

  return result
}

function formatInlineMarkdown(text: string): string {
  let s = text
  // inline code: `code`
  s = s.replace(/`([^`]+)`/g, (_m, c) => `<code class="px-1.5 py-0.5 rounded bg-surface-container-high border border-outline-variant/40 font-mono text-[11px] text-primary">${escapeHtml(c)}</code>`)
  // bold: **text**
  s = s.replace(/\*\*([^*]+)\*\*/g, '<strong class="font-bold text-on-surface">$1</strong>')
  // italic: *text*
  s = s.replace(/(^|[^*])\*([^*]+)\*/g, '$1<em class="italic">$2</em>')
  // links: [text](url)
  s = s.replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" class="text-primary hover:underline font-medium" target="_blank" rel="noopener">$1</a>')
  return s
}

function convertMarkdownSnippetToHtml(md: string): string {
  const codeBlocks: string[] = []

  // 1. Code blocks ```yaml ... ``` or ```svg
  let html = md.replace(/```([a-z]*)\n([\s\S]*?)```/g, (_match, lang, code) => {
    if (lang === 'svg' || code.trim().startsWith('<svg')) {
      const blockHtml = `
        <div class="my-5 p-4 rounded-2xl bg-surface-container-low border border-outline-variant/60 shadow-lg overflow-x-auto flex justify-center items-center">
          ${code.trim()}
        </div>
      `
      const placeholder = `___CODE_BLOCK_${codeBlocks.length}___`
      codeBlocks.push(blockHtml)
      return placeholder
    }

    if (lang === 'mermaid') {
      const safeCode = escapeHtml(code.trim())
      const blockHtml = `
        <div class="my-5 p-4 rounded-2xl bg-surface-container-low border border-outline-variant/60 shadow-lg overflow-x-auto flex justify-center items-center">
          <pre class="mermaid mermaid-diagram">${safeCode}</pre>
        </div>
      `
      const placeholder = `___CODE_BLOCK_${codeBlocks.length}___`
      codeBlocks.push(blockHtml)
      return placeholder
    }

    const safeCode = escapeHtml(code.trim())
    const blockHtml = `
      <div class="my-3 rounded-lg bg-surface-container-highest border border-outline-variant/60 overflow-hidden font-mono text-xs">
        <div class="px-3 py-1 bg-surface-variant/80 border-b border-outline-variant/40 flex items-center justify-between text-[10px] text-on-surface-variant font-bold uppercase">
          <span>${lang || 'code'}</span>
        </div>
        <pre class="p-3 overflow-x-auto text-primary-bright font-mono text-[11px] leading-snug"><code>${safeCode}</code></pre>
      </div>
    `
    const placeholder = `___CODE_BLOCK_${codeBlocks.length}___`
    codeBlocks.push(blockHtml)
    return placeholder
  })

  // 2. Markdown tables (| header | header |)
  html = html.replace(/(?:^|\n)((?:\|.+?\|\s*(?:\n|$))+)/g, (_match, tableBlock) => {
    const rawLines = tableBlock.trim().split('\n').map((l: string) => l.trim()).filter(Boolean)
    if (rawLines.length < 2) return tableBlock

    const separatorIdx = rawLines.findIndex((l: string) => /^\|?\s*:?-+:?\s*(?:\|\s*:?-+:?\s*)+\|?$/.test(l))
    if (separatorIdx === -1) return tableBlock

    const headerLine = rawLines[0]
    const alignSpecs = rawLines[separatorIdx]
      .split('|')
      .slice(1, -1)
      .map((col: string) => {
        const c = col.trim()
        if (c.startsWith(':') && c.endsWith(':')) return 'text-center'
        if (c.endsWith(':')) return 'text-right'
        return 'text-left'
      })

    const headers = headerLine
      .split('|')
      .slice(1, -1)
      .map((h: string) => h.trim())

    const dataLines = rawLines.filter((_: string, idx: number) => idx !== 0 && idx !== separatorIdx)

    const ths = headers
      .map((h: string, i: number) => {
        const align = alignSpecs[i] || 'text-left'
        return `<th class="px-3.5 py-2.5 ${align} font-mono text-[11px] font-bold text-on-surface uppercase tracking-wider border-b border-outline-variant/60 bg-surface-container-high/90">${formatInlineMarkdown(h)}</th>`
      })
      .join('')

    const trs = dataLines
      .map((line: string) => {
        const cells = line.split('|').slice(1, -1).map((c: string) => c.trim())
        const tds = cells
          .map((cell: string, i: number) => {
            const align = alignSpecs[i] || 'text-left'
            return `<td class="px-3.5 py-2.5 text-xs border-b border-outline-variant/30 text-on-surface-variant ${align}">${formatInlineMarkdown(cell)}</td>`
          })
          .join('')
        return `<tr class="hover:bg-surface-container-high/40 transition-colors">${tds}</tr>`
      })
      .join('')

    return `\n<div class="my-4 overflow-x-auto rounded-xl border border-outline-variant/60 bg-surface-container-low shadow-sm"><table class="w-full border-collapse text-left text-xs"><thead><tr>${ths}</tr></thead><tbody class="divide-y divide-outline-variant/20">${trs}</tbody></table></div>\n`
  })

  // 3. Important / Alert blocks > [!IMPORTANT]
  html = html.replace(/^>\s*\[!(IMPORTANT|NOTE|WARNING)\]\s*\n([\s\S]*?)(?=\n\n|\n#|$)/gm, (_m, type, content) => {
    const borderColor = type === 'IMPORTANT' ? 'border-primary' : type === 'WARNING' ? 'border-warning' : 'border-secondary'
    const bgColor = type === 'IMPORTANT' ? 'bg-primary/10' : type === 'WARNING' ? 'bg-warning/10' : 'bg-secondary/10'
    const icon = type === 'IMPORTANT' ? 'priority_high' : type === 'WARNING' ? 'warning' : 'info'
    const cleanContent = formatInlineMarkdown(content.replace(/^>\s*/gm, '').trim())
    return `
      <div class="my-3 p-3 rounded-lg border-l-4 ${borderColor} ${bgColor} flex items-start gap-2.5 text-xs text-on-surface">
        <span class="material-symbols-outlined text-sm flex-shrink-0 mt-0.5">${icon}</span>
        <div>${cleanContent}</div>
      </div>
    `
  })

  // 4. Headings #### and ###
  html = html.replace(/^####\s+(.*$)/gm, (_m, h) => `<h4 class="text-xs font-bold text-on-surface mt-3 mb-1.5">${formatInlineMarkdown(h)}</h4>`)
  html = html.replace(/^###\s+(.*$)/gm, (_m, h) => `<h3 class="text-sm font-bold text-on-surface mt-4 mb-2">${formatInlineMarkdown(h)}</h3>`)

  // 5. Lists (unordered, ordered, nested, checkboxes)
  html = html.replace(/(?:^|\n)((?:\s*(?:[-*]|\d+\.)\s+.+(?:\n|$))+)/g, (_match: string, listBlock: string) => {
    const rawLines = listBlock.trim().split('\n')
    if (rawLines.length === 0) return listBlock

    const isOrdered = /^\s*\d+\./.test(rawLines[0].trim())
    const tag = isOrdered ? 'ol' : 'ul'

    const itemsHtml = rawLines.map((line: string) => {
      const trimmed = line.trim()

      // Checkbox item: - [ ] or - [x]
      const checkboxMatch = trimmed.match(/^[-*]\s+\[([ xX])\]\s+(.*)/)
      if (checkboxMatch) {
        const isChecked = checkboxMatch[1].toLowerCase() === 'x'
        const content = formatInlineMarkdown(checkboxMatch[2])
        const icon = isChecked ? 'check_box' : 'check_box_outline_blank'
        const iconColor = isChecked ? 'text-primary' : 'text-on-surface-variant/60'
        return `<li class="flex items-start gap-2 text-xs text-on-surface-variant my-1">
          <span class="material-symbols-outlined text-sm shrink-0 mt-0.5 ${iconColor}">${icon}</span>
          <span class="${isChecked ? 'line-through opacity-75' : ''}">${content}</span>
        </li>`
      }

      // Unordered item: - or *
      const bulletMatch = trimmed.match(/^[-*]\s+(.*)/)
      if (bulletMatch) {
        const content = formatInlineMarkdown(bulletMatch[1])
        const isIndent = line.startsWith('  ') || line.startsWith('\t')
        const indentClass = isIndent ? 'ml-6 list-circle' : 'ml-4 list-disc'
        return `<li class="${indentClass} text-xs text-on-surface-variant leading-relaxed my-1">${content}</li>`
      }

      // Ordered item: 1. 2.
      const numberMatch = trimmed.match(/^\d+\.\s+(.*)/)
      if (numberMatch) {
        const content = formatInlineMarkdown(numberMatch[1])
        return `<li class="ml-5 list-decimal text-xs text-on-surface-variant leading-relaxed my-1">${content}</li>`
      }

      return `<li class="ml-4 text-xs text-on-surface-variant leading-relaxed my-1">${formatInlineMarkdown(trimmed)}</li>`
    }).join('')

    const listClass = isOrdered
      ? 'my-3 space-y-1 pl-1 font-sans text-xs text-on-surface-variant'
      : 'my-3 space-y-1 pl-1 font-sans text-xs text-on-surface-variant'

    return `\n<${tag} class="${listClass}">${itemsHtml}</${tag}>\n`
  })

  // 6. Inline formatting outside tables and code block placeholders
  const lines = html.split('\n')
  html = lines.map(line => {
    if (line.startsWith('<') || line.includes('___CODE_BLOCK_')) return line
    return formatInlineMarkdown(line)
  }).join('\n')

  // 7. Paragraphs
  html = html.replace(/\n\n/g, '<br/><br/>')

  // 8. Restore Code blocks
  codeBlocks.forEach((block, idx) => {
    html = html.replace(`___CODE_BLOCK_${idx}___`, block)
  })

  return html
}

function scrollToSection(id: string) {
  activeSection.value = id
  const el = document.getElementById(id)
  if (el) {
    el.scrollIntoView({ behavior: 'smooth' })
  }
}

async function selectArticle(art: WikiArticleItem) {
  currentArticlePath.value = art.path
  currentArticleTitle.value = art.title
  await loadArticleContent(art.path)
}

async function renderMermaid() {
  await nextTick()
  try {
    const nodes = document.querySelectorAll('.mermaid-diagram')
    if (nodes.length > 0) {
      await mermaid.run({
        nodes: Array.from(nodes) as HTMLElement[],
      })
    }
  } catch (err) {
    console.error('Failed to render mermaid diagrams:', err)
  }
}

async function loadArticleContent(path: string) {
  loading.value = true
  error.value = null
  try {
    const res = await apiFetchWikiArticle(path)
    sections.value = parseMarkdownToSections(res.content)
    if (sections.value.length > 0) {
      activeSection.value = sections.value[0].id
    }
  } catch (err: any) {
    console.error('Error fetching wiki article:', err)
    error.value = err?.response?.data?.detail || err?.message || t('wikiError')
  } finally {
    loading.value = false
    await renderMermaid()
  }
}

async function reloadCurrentArticle() {
  await loadArticleContent(currentArticlePath.value)
}

async function initWiki() {
  try {
    const treeRes = await apiFetchWikiTree()
    categories.value = treeRes.categories || []
    if (categories.value.length > 0 && categories.value[0].articles.length > 0) {
      const firstArt = categories.value[0].articles[0]
      currentArticlePath.value = firstArt.path
      currentArticleTitle.value = firstArt.title
    }
    await loadArticleContent(currentArticlePath.value)
  } catch (err) {
    console.error('Failed to load wiki tree:', err)
    await loadArticleContent(currentArticlePath.value)
  }
}

watch(currentLang, () => {
  initWiki()
})

onMounted(() => {
  initWiki()
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
.doc-body :deep(pre),
.doc-body :deep(code) {
  font-family: 'Consolas', 'Courier New', ui-monospace, SFMono-Regular, Menlo, Monaco, monospace;
  font-variant-east-asian: normal;
  letter-spacing: 0;
  line-height: 1.35;
}
</style>
