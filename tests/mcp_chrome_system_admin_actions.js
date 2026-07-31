const puppeteer = require('puppeteer-core');
const path = require('path');
const { execSync } = require('child_process');

const ARTIFACTS_DIR = '/home/ttc/.gemini/antigravity-ide/brain/bf797eb8-e66f-4f42-a027-94fd460f7848';

async function runSystemAdminUiTest() {
  console.log('🚀 Запуск интерактивного UI тестирования компонента "Системное администрирование" в Chromium GUI...');

  const rootToken = execSync(`PYTHONPATH=. .venv/bin/python -c 'from backend.core.database import get_db_connection; from backend.core.auth import create_access_token; conn = get_db_connection(); root = conn.execute("SELECT id, username FROM users WHERE username = \\"root\\"").fetchone(); print(create_access_token(root["id"], root["username"]))'`, { cwd: '/opt/nms-webui' }).toString().trim();

  const user = {
    id: "usr-root-01",
    username: "root",
    full_name: "Главный администратор (Root)",
    email: "root@nms.local",
    uid: "ROOT-001",
    role_id: "1",
    role_name: "Administrator",
    permissions: ["*"]
  };

  const browser = await puppeteer.launch({
    executablePath: '/usr/bin/chromium-browser',
    headless: false,
    env: { ...process.env, DISPLAY: ':0' },
    args: [
      '--no-sandbox',
      '--disable-setuid-sandbox',
      '--disable-gpu',
      '--window-size=1280,850',
      '--window-position=100,100'
    ]
  });

  const page = await browser.newPage();
  await page.setViewport({ width: 1280, height: 800 });

  const delay = (ms) => new Promise(r => setTimeout(r, ms));

  try {
    // 1. Авторизация root
    console.log('📌 1. Загрузка сессии и открытие "/settings/system"');
    await page.goto('http://localhost:5173/login', { waitUntil: 'domcontentloaded' });
    await page.evaluate((authToken, authUser) => {
      localStorage.setItem('nms_token', authToken);
      localStorage.setItem('nms_user', JSON.stringify(authUser));
      sessionStorage.setItem('nms_token', authToken);
      sessionStorage.setItem('nms_user', JSON.stringify(authUser));
    }, rootToken, user);

    await page.goto('http://localhost:5173/settings/system', { waitUntil: 'domcontentloaded' });
    await page.waitForSelector('h1', { timeout: 10000 });
    await delay(1000);

    const shotOverview = path.join(ARTIFACTS_DIR, '20_system_admin_overview.png');
    await page.screenshot({ path: shotOverview, fullPage: true });
    console.log(`   📸 Скриншот общего вида панели управления: ${shotOverview}`);

    // 2. Интерактивное скачивание бэкапа
    console.log('📌 2. Интерактивный клик по кнопке "Скачать бэкап"');
    const downloadBtn = await page.$('button.bg-primary');
    if (downloadBtn) {
      await downloadBtn.click();
      await delay(1500);
      const shotBackup = path.join(ARTIFACTS_DIR, '21_backup_downloaded.png');
      await page.screenshot({ path: shotBackup, fullPage: true });
      console.log(`   📸 Скриншот вызова резервного копирования: ${shotBackup}`);
    }

    // 3. Инспекция карточки активных сессий
    console.log('📌 3. Проверка панели системных сессий подключений');
    const shotSessions = path.join(ARTIFACTS_DIR, '22_active_sessions_monitored.png');
    await page.screenshot({ path: shotSessions, fullPage: true });
    console.log(`   📸 Скриншот монитора сессий: ${shotSessions}`);

    // 4. Интерактивное управление фильтрами системных логов
    console.log('📌 4. Взаимодействие с терминалом логов: выбор уровня и живой поиск...');
    
    // Выбор уровня лога INFO / ERROR
    const selects = await page.$$('select');
    if (selects.length >= 2) {
      console.log('   - Изменение уровня логирования на INFO...');
      await selects[1].select('INFO');
      await delay(1000);
    }

    // Ввод поисковой строки "GET"
    const searchInput = await page.$('input[placeholder="Поиск в логах..."]');
    if (searchInput) {
      console.log('   - Ввод текста "GET" в строку фильтра логов...');
      await searchInput.type('GET');
      await delay(1000);
    }

    // Нажатие кнопки обновить
    const refreshBtn = await page.$('button[title="Обновить"]');
    if (refreshBtn) {
      console.log('   - Клик по кнопке "Обновить данные логов"');
      await refreshBtn.click();
      await delay(1500);
    }

    const shotLogsDone = path.join(ARTIFACTS_DIR, '23_system_logs_filtered_and_searched.png');
    await page.screenshot({ path: shotLogsDone, fullPage: true });
    console.log(`   📸 Скриншот терминала логов с примененными фильтрами: ${shotLogsDone}`);

    console.log('\n🎉 Интерактивное UI-тестирование панели "Системное администрирование" успешно завершено!');

  } catch (err) {
    console.error('❌ Ошибка UI автоматизации:', err);
    process.exitCode = 1;
  } finally {
    await browser.close();
  }
}

runSystemAdminUiTest();
