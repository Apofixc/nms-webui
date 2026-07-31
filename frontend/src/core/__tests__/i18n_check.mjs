import fs from 'fs'

const ruContent = fs.readFileSync('/opt/nms-webui/frontend/src/core/locales/ru.ts', 'utf8')
const enContent = fs.readFileSync('/opt/nms-webui/frontend/src/core/locales/en.ts', 'utf8')

function extractKeys(str) {
  const keys = []
  const lines = str.split('\n')
  for (const line of lines) {
    const trimmed = line.trim()
    if (!trimmed || trimmed.startsWith('//')) continue
    const match = trimmed.match(/^['"]?([a-zA-Z0-9_\-\.]+?)['"]?:\s*['"`]/)
    if (match) {
      keys.push(match[1])
    }
  }
  return keys
}

const ruKeys = extractKeys(ruContent)
const enKeys = extractKeys(enContent)

console.log(`RU Keys count: ${ruKeys.length}`)
console.log(`EN Keys count: ${enKeys.length}`)

const ruSet = new Set(ruKeys)
const enSet = new Set(enKeys)

const missingInEn = ruKeys.filter((k) => !enSet.has(k))
const missingInRu = enKeys.filter((k) => !ruSet.has(k))

if (missingInEn.length > 0) {
  console.error('Keys in RU missing in EN:', missingInEn)
  process.exit(1)
}

if (missingInRu.length > 0) {
  console.error('Keys in EN missing in RU:', missingInRu)
  process.exit(1)
}

console.log('SUCCESS: RU and EN keys are 100% synchronized and symmetrical!')
