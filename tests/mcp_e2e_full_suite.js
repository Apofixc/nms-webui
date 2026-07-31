const puppeteer = require('puppeteer-core');
const path = require('path');
const fs = require('fs');
const { execSync } = require('child_process');

// Директория артефактов для текущей сессии
const ARTIFACTS_DIR = '/home/ttc/.gemini/antigravity-ide/brain/bf797eb8-e66f-4f42-a027-94fd460f7848';

if (!fs.existsSync(ARTIFACTS_DIR)) {
  fs.mkdirSync(ARTIFACTS_DIR, { recursive: true });
}

async function runFullMcpE2eTestSuite() {
  console.log('🚀 [E2E MCP Test Suite] Запуск полного комплексного E2E-теста NMS-WebUI в Chromium GUI...');

  // 1. Сброс пароля root и генерация валидного токена доступа
  execSync('PYTHONPATH=. .venv/bin/python -c "from backend.scripts.reset_root import reset_root_account; reset_root_account()"', { cwd: '/opt/nms-webui' });

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

  console.log(`✅ Токен суперпользователя (root) успешно получен.`);

  // 2. Запуск браузера Chromium (GUI mode DISPLAY=:0)
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

  let passedSteps = 0;
  let totalSteps = 0;

  function stepLog(stepNum, name, status = 'OK') {
    totalSteps++;
    if (status === 'OK') passedSteps++;
    console.log(`  [Шаг ${stepNum}] ${name}: ${status === 'OK' ? '✅ УСПЕШНО' : '❌ ОШИБКА'}`);
  }

  try {
    // =========================================================================
    // ЭТАП 1: Авторизация и Главный Дашборд
    // =========================================================================
    console.log('\n--- ЭТАП 1: Аутентификация и Дашборд ---');
    await page.goto('http://localhost:5173/login', { waitUntil: 'domcontentloaded' });
    await page.evaluate((token, userData) => {
      localStorage.setItem('nms_token', token);
      localStorage.setItem('nms_user', JSON.stringify(userData));
      sessionStorage.setItem('nms_token', token);
      sessionStorage.setItem('nms_user', JSON.stringify(userData));
    }, rootToken, user);

    await page.goto('http://localhost:5173/', { waitUntil: 'networkidle2' });
    await page.waitForSelector('h1', { timeout: 10000 });
    const dashShot = path.join(ARTIFACTS_DIR, 'e2e_01_dashboard.png');
    await page.screenshot({ path: dashShot, fullPage: true });
    stepLog(1, 'Авторизация и загрузка Дашборда');

    // =========================================================================
    // ЭТАП 2: Политики безопасности (/settings)
    // =========================================================================
    console.log('\n--- ЭТАП 2: Вкладка "Доступ и Идентификация" (/settings) ---');
    await page.goto('http://localhost:5173/settings', { waitUntil: 'networkidle2' });
    await page.waitForSelector('h1', { timeout: 10000 });
    const setShot = path.join(ARTIFACTS_DIR, 'e2e_02_access_security_settings.png');
    await page.screenshot({ path: setShot, fullPage: true });
    stepLog(2, 'Загрузка настроек доступа и безопасности');

    // =========================================================================
    // ЭТАП 3: Управление пользователями (/settings/users)
    // =========================================================================
    console.log('\n--- ЭТАП 3: Управление пользователями (/settings/users) ---');
    await page.goto('http://localhost:5173/settings/users', { waitUntil: 'networkidle2' });
    await page.waitForSelector('h1', { timeout: 10000 });
    const usersShot1 = path.join(ARTIFACTS_DIR, 'e2e_03_users_table.png');
    await page.screenshot({ path: usersShot1, fullPage: true });
    stepLog(3, 'Отображение реестра пользователей');

    // Нажатие кнопки "Добавить пользователя"
    const addBtn = await page.$('button.bg-primary');
    if (addBtn) {
      await addBtn.click();
      await delay(800);
      const modalShot = path.join(ARTIFACTS_DIR, 'e2e_04_create_user_modal.png');
      await page.screenshot({ path: modalShot, fullPage: true });
      stepLog(4, 'Открытие модального окна создания пользователя');

      // Закрытие модального окна (отмена)
      const cancelBtn = await page.$('button[type="button"]');
      if (cancelBtn) await cancelBtn.click();
      await delay(500);
    }

    // =========================================================================
    // ЭТАП 4: Системное администрирование (/settings/system)
    // =========================================================================
    console.log('\n--- ЭТАП 4: Системное администрирование (/settings/system) ---');
    await page.goto('http://localhost:5173/settings/system', { waitUntil: 'networkidle2' });
    await page.waitForSelector('h1', { timeout: 10000 });
    
    // Взаимодействие с терминалом логов
    const searchInput = await page.$('input[placeholder="Поиск в логах..."]');
    if (searchInput) {
      await searchInput.type('auth');
      await delay(500);
    }
    const sysShot = path.join(ARTIFACTS_DIR, 'e2e_05_system_admin_logs.png');
    await page.screenshot({ path: sysShot, fullPage: true });
    stepLog(5, 'Инспекция панели администрирования и фильтрации системных логов');

    // =========================================================================
    // ЭТАП 5: Профиль пользователя (/settings/profile)
    // =========================================================================
    console.log('\n--- ЭТАП 5: Профиль пользователя (/settings/profile) ---');
    await page.goto('http://localhost:5173/settings/profile', { waitUntil: 'networkidle2' });
    await page.waitForSelector('h1', { timeout: 10000 });
    const profShot = path.join(ARTIFACTS_DIR, 'e2e_06_user_profile.png');
    await page.screenshot({ path: profShot, fullPage: true });
    stepLog(6, 'Отображение страницы профиля администратора');

    // =========================================================================
    // ЭТАП 6: Управление модулями (/modules)
    // =========================================================================
    console.log('\n--- ЭТАП 6: Модули системы (/modules) ---');
    await page.goto('http://localhost:5173/modules', { waitUntil: 'networkidle2' });
    await page.waitForSelector('h1', { timeout: 10000 });
    const modShot = path.join(ARTIFACTS_DIR, 'e2e_07_modules_management.png');
    await page.screenshot({ path: modShot, fullPage: true });
    stepLog(7, 'Отображение реестра модулей NMS');

    console.log(`\n🎉 [ИТОГ E2E-ТЕСТИРОВАНИЯ]: Пройдено ${passedSteps} из ${totalSteps} проверок без ошибок!`);

  } catch (err) {
    console.error('❌ [E2E-ОШИБКА]:', err);
    process.exitCode = 1;
  } finally {
    await browser.close();
  }
}

runFullMcpE2eTestSuite();
