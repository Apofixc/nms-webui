const puppeteer = require('puppeteer-core');
const path = require('path');
const fs = require('fs');
const { execSync } = require('child_process');

const ARTIFACTS_DIR = '/home/ttc/.gemini/antigravity-ide/brain/061103f1-2c39-4924-949b-f517af354cc5';

async function runMcpChromeTest() {
  console.log('🚀 Запуск ВСЕОБЩЕГО видимого браузера Chromium (GUI) на DISPLAY=:0...');

  // 1. Сброс пароля root и генерация валидного токена доступа
  execSync('PYTHONPATH=. .venv/bin/python -c "from backend.scripts.reset_root import reset_root_account; reset_root_account()"', { cwd: '/opt/nms-webui' });
  
  const token = execSync(`PYTHONPATH=. .venv/bin/python -c 'from backend.core.database import get_db_connection; from backend.core.auth import create_access_token; conn = get_db_connection(); root = conn.execute("SELECT id, username FROM users WHERE username = \\"root\\"").fetchone(); print(create_access_token(root["id"], root["username"]))'`, { cwd: '/opt/nms-webui' }).toString().trim();

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

  console.log(`✅ Токен сессии получен: ${token.substring(0, 20)}...`);

  // 2. Запуск ВИДИМОГО браузера Chromium (headless: false) на экране пользователя
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
    // 3. Открытие и авторизация
    console.log('📌 1. Загрузка и авторизация сессии...');
    await page.goto('http://localhost:5173/login', { waitUntil: 'domcontentloaded' });
    await page.evaluate((authToken, authUser) => {
      localStorage.setItem('nms_token', authToken);
      localStorage.setItem('nms_user', JSON.stringify(authUser));
      sessionStorage.setItem('nms_token', authToken);
      sessionStorage.setItem('nms_user', JSON.stringify(authUser));
    }, token, user);

    // =========================================================================
    // 4. Вкладка 1: Доступ и Идентификация (/settings/access-control)
    // =========================================================================
    console.log('📌 2. Открытие Вкладки 1: "Доступ и Идентификация" (/settings/access-control)');
    await page.goto('http://localhost:5173/settings/access-control', { waitUntil: 'networkidle2' });
    await page.waitForSelector('h1');
    await page.screenshot({ path: path.join(ARTIFACTS_DIR, 'tab1_access_identity.png'), fullPage: true });
    console.log('   📺 Вкладка 1 отображается на экране пользователя!');
    await delay(2000);

    // =========================================================================
    // 5. Вкладка 2: Управление пользователями (/settings/users)
    // =========================================================================
    console.log('📌 3. Открытие Вкладки 2: "Управление пользователями" (/settings/users)');
    await page.goto('http://localhost:5173/settings/users', { waitUntil: 'networkidle2' });
    await page.waitForSelector('h1');
    await page.screenshot({ path: path.join(ARTIFACTS_DIR, 'tab2_users_management.png'), fullPage: true });
    console.log('   📺 Вкладка 2 отображается на экране пользователя!');
    await delay(2000);

    // =========================================================================
    // 6. Вкладка 3: Системное администрирование (/settings/system)
    // =========================================================================
    console.log('📌 4. Открытие Вкладки 3: "Системное администрирование" (/settings/system)');
    await page.goto('http://localhost:5173/settings/system', { waitUntil: 'networkidle2' });
    await page.waitForSelector('h1');
    await page.screenshot({ path: path.join(ARTIFACTS_DIR, 'tab3_system_admin.png'), fullPage: true });
    console.log('   📺 Вкладка 3 отображается на экране пользователя!');
    await delay(2000);

    // =========================================================================
    // 7. Вкладка 4: Профиль пользователя (/settings/profile)
    // =========================================================================
    console.log('📌 5. Открытие Вкладки 4: "Профиль пользователя" (/settings/profile)');
    await page.goto('http://localhost:5173/settings/profile', { waitUntil: 'networkidle2' });
    await page.waitForSelector('h1');
    await page.screenshot({ path: path.join(ARTIFACTS_DIR, 'tab4_user_profile.png'), fullPage: true });
    console.log('   📺 Вкладка 4 отображается на экране пользователя!');
    await delay(2000);

    console.log('\n🎉 Визуальная демонстрация 4 вкладок в браузере Chromium завершена!');

  } catch (err) {
    console.error('❌ Ошибка тестирования:', err);
    process.exitCode = 1;
  } finally {
    await browser.close();
  }
}

runMcpChromeTest();
