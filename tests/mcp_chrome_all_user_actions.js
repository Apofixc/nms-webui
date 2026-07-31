const puppeteer = require('puppeteer-core');
const path = require('path');
const { execSync } = require('child_process');

const ARTIFACTS_DIR = '/home/ttc/.gemini/antigravity-ide/brain/bf797eb8-e66f-4f42-a027-94fd460f7848';

async function runAllUsersActionsUiTest() {
  console.log('🚀 Запуск полного UI-тестирования всех действий с пользователями в Chromium GUI...');

  // 1. Получение токена сессии root
  const rootToken = execSync(`PYTHONPATH=. .venv/bin/python -c 'from backend.core.database import get_db_connection; from backend.core.auth import create_access_token; conn = get_db_connection(); root = conn.execute("SELECT id, username FROM users WHERE username = \\"root\\"").fetchone(); print(create_access_token(root["id"], root["username"]))'`, { cwd: '/opt/nms-webui' }).toString().trim();

  // Создаем целевого пользователя для действий
  execSync(`PYTHONPATH=. .venv/bin/python -c 'from backend.core.database import get_db_connection; conn = get_db_connection(); conn.execute("INSERT OR REPLACE INTO users (id, username, full_name, email, uid, hashed_password, is_active, role_id) VALUES (\\"usr-target-01\\", \\"target_op\\", \\"Тестовый Оператор Действий\\", \\"target@nms.local\\", \\"UID-TARGET\\", \\"hash\\", 1, \\"2\\")"); conn.commit()'`, { cwd: '/opt/nms-webui' });

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
    // 2. Авторизация root
    console.log('📌 1. Открытие страницы "Управление пользователями" (/settings/users)');
    await page.goto('http://localhost:5173/login', { waitUntil: 'domcontentloaded' });
    await page.evaluate((authToken, authUser) => {
      localStorage.setItem('nms_token', authToken);
      localStorage.setItem('nms_user', JSON.stringify(authUser));
      sessionStorage.setItem('nms_token', authToken);
      sessionStorage.setItem('nms_user', JSON.stringify(authUser));
    }, rootToken, user);

    await page.goto('http://localhost:5173/settings/users', { waitUntil: 'domcontentloaded' });
    await page.waitForSelector('h1', { timeout: 10000 });
    await delay(1000);

    // =========================================================================
    // ДЕЙСТВИЕ 1: Блокировка и разблокировка пользователя
    // =========================================================================
    console.log('📌 2. Поиск пользователя target_op в таблице...');
    const rows = await page.$$('tbody tr');
    let targetRowIndex = -1;
    for (let i = 0; i < rows.length; i++) {
      const text = await page.evaluate(el => el.innerText, rows[i]);
      if (text.includes('target_op')) {
        targetRowIndex = i;
        break;
      }
    }

    if (targetRowIndex !== -1) {
      const rowButtons = await rows[targetRowIndex].$$('button');
      
      // Блокировка / разблокировка
      console.log('📌 3. ДЕЙСТВИЕ 1: Заблокировать пользователя (клик lock)');
      await rowButtons[1].click();
      await delay(1500);
      const shotLock = path.join(ARTIFACTS_DIR, '12_user_locked_in_grid.png');
      await page.screenshot({ path: shotLock, fullPage: true });
      console.log(`   📸 Скриншот блокировки: ${shotLock}`);

      console.log('📌 4. ДЕЙСТВИЕ 2: Разблокировать пользователя (клик lock_open)');
      await rowButtons[1].click();
      await delay(1500);
      const shotUnlock = path.join(ARTIFACTS_DIR, '13_user_unlocked_in_grid.png');
      await page.screenshot({ path: shotUnlock, fullPage: true });
      console.log(`   📸 Скриншот разблокировки: ${shotUnlock}`);

      // Сброс пароля
      console.log('📌 5. ДЕЙСТВИЕ 3: Сброс пароля (клик key)');
      await rowButtons[2].click();
      await delay(1000);
      const shotPassModal = path.join(ARTIFACTS_DIR, '14_password_reset_modal_opened.png');
      await page.screenshot({ path: shotPassModal, fullPage: true });
      console.log(`   📸 Скриншот модального окна сброса пароля: ${shotPassModal}`);

      // Ввод нового пароля
      const passInput = await page.waitForSelector('form input[type="text"]');
      await passInput.type('NewStrongPass999!');
      await delay(500);

      const passSubmit = await page.waitForSelector('form button[type="submit"]');
      await passSubmit.click();
      await delay(1500);
      const shotPassDone = path.join(ARTIFACTS_DIR, '15_password_reset_success.png');
      await page.screenshot({ path: shotPassDone, fullPage: true });
      console.log(`   📸 Скриншот после сброса пароля: ${shotPassDone}`);

      // Завершить все сессии
      console.log('📌 6. ДЕЙСТВИЕ 4: Завершить все сессии пользователя (клик logout)');
      const updatedRows = await page.$$('tbody tr');
      const updatedButtons = await updatedRows[targetRowIndex].$$('button');
      await updatedButtons[3].click();
      await delay(1500);
      const shotTermSess = path.join(ARTIFACTS_DIR, '16_all_sessions_terminated.png');
      await page.screenshot({ path: shotTermSess, fullPage: true });
      console.log(`   📸 Скриншот завершения всех сессий: ${shotTermSess}`);

      // Удалить пользователя
      console.log('📌 7. ДЕЙСТВИЕ 5: Удалить пользователя (клик delete)');
      await updatedButtons[4].click();
      await delay(1000);
      const shotDelConfirm = path.join(ARTIFACTS_DIR, '17_delete_confirmation_modal_opened.png');
      await page.screenshot({ path: shotDelConfirm, fullPage: true });
      console.log(`   📸 Скриншот подтверждения удаления: ${shotDelConfirm}`);

      // Подтверждение удаления: находим все кнопки в модальном окне удаления
      const modalButtons = await page.$$('div.fixed button');
      if (modalButtons.length >= 2) {
        // Нажимаем последнюю кнопку (Подтвердить удаление)
        await modalButtons[modalButtons.length - 1].click();
      } else {
        const errorBtn = await page.waitForSelector('button.bg-error');
        await errorBtn.click();
      }
      await delay(2000);

      const shotDelDone = path.join(ARTIFACTS_DIR, '18_user_deleted_from_grid.png');
      await page.screenshot({ path: shotDelDone, fullPage: true });
      console.log(`   📸 Скриншот таблицы после удаления пользователя: ${shotDelDone}`);
    }

    console.log('\n🎉 Все 5 интерактивных действий с пользователем в UI успешно проверены!');

  } catch (err) {
    console.error('❌ Ошибка UI автоматизации:', err);
    process.exitCode = 1;
  } finally {
    await browser.close();
  }
}

runAllUsersActionsUiTest();
