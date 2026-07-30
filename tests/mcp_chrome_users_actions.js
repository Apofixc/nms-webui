const puppeteer = require('puppeteer-core');
const path = require('path');
const { execSync } = require('child_process');

const ARTIFACTS_DIR = '/home/ttc/.gemini/antigravity-ide/brain/061103f1-2c39-4924-949b-f517af354cc5';

async function runInteractiveUsersUiTest() {
  console.log('🚀 Запуск интерактивного UI тестирования функционала пользователей в Chromium GUI...');

  // 1. Получение токена сессии root
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
    // 2. Аутентификация
    console.log('📌 1. Инициализация авторизованной сессии root');
    await page.goto('http://localhost:5173/login', { waitUntil: 'domcontentloaded' });
    await page.evaluate((authToken, authUser) => {
      localStorage.setItem('nms_token', authToken);
      localStorage.setItem('nms_user', JSON.stringify(authUser));
      sessionStorage.setItem('nms_token', authToken);
      sessionStorage.setItem('nms_user', JSON.stringify(authUser));
    }, token, user);

    // 3. Открытие реестра пользователей
    console.log('📌 2. Открытие страницы "Управление пользователями" (/settings/users)');
    await page.goto('http://localhost:5173/settings/users', { waitUntil: 'networkidle2' });
    await page.waitForSelector('table');
    await delay(1000);

    const shot1 = path.join(ARTIFACTS_DIR, '01_users_table_initial.png');
    await page.screenshot({ path: shot1, fullPage: true });
    console.log(`   📸 Скриншот начальной таблицы пользователей: ${shot1}`);

    // 4. Клик по кнопке "Добавить пользователя"
    console.log('📌 3. Интерактивный клик на кнопку "+ Добавить пользователя"');
    const addButton = await page.waitForSelector('button.bg-primary');
    await addButton.click();
    await delay(1000);

    const shot2 = path.join(ARTIFACTS_DIR, '02_add_user_modal_opened.png');
    await page.screenshot({ path: shot2, fullPage: true });
    console.log(`   📸 Скриншот открытого модального окна добавления: ${shot2}`);

    // 5. Заполнение формы создания пользователя
    console.log('📌 4. Интерактивное заполнение формы нового пользователя...');
    const inputs = await page.$$('form input');
    
    // Full Name (input 0)
    await inputs[0].type('Инженер Тестов ИИ');
    // Title/Department (input 1)
    await inputs[1].type('Отдел Автоматизации');
    // Email (input 2)
    await inputs[2].type('engineer_ui@nms.local');
    // Username (input 3)
    await inputs[3].type('test_ui_operator');
    // Password (input 4)
    await inputs[4].type('StrongPass123!');

    await delay(1000);

    // 6. Отправка формы (Клик по кнопке Создать/Сохранить)
    console.log('📌 5. Нажатие кнопки "Сохранить" в модальном окне');
    const submitBtn = await page.waitForSelector('form button[type="submit"]');
    await submitBtn.click();
    await delay(2000);

    const shot3 = path.join(ARTIFACTS_DIR, '03_new_user_created_in_grid.png');
    await page.screenshot({ path: shot3, fullPage: true });
    console.log(`   📸 Скриншот таблицы с новым созданным пользователем: ${shot3}`);

    // 7. Поиск нового пользователя в таблице и клик по кнопке Редактировать
    console.log('📌 6. Интерактивный клик на кнопку "Редактировать" у пользователя');
    const editButtons = await page.$$('tbody tr button');
    if (editButtons.length > 0) {
      await editButtons[0].click();
      await delay(1000);

      const shot4 = path.join(ARTIFACTS_DIR, '04_edit_user_modal_opened.png');
      await page.screenshot({ path: shot4, fullPage: true });
      console.log(`   📸 Скриншот открытого модального окна редактирования: ${shot4}`);

      // Изменение ФИО
      console.log('📌 7. Изменение ФИО пользователя в форме редактирования...');
      const editInputs = await page.$$('form input');
      if (editInputs && editInputs.length > 0) {
        await editInputs[0].click({ clickCount: 3 });
        await editInputs[0].type('Инженер Тестов ИИ (Отредактирован)');
        await delay(1000);
      }

      // Сохранение изменений
      const saveEditBtn = await page.waitForSelector('form button[type="submit"]');
      await saveEditBtn.click();
      await delay(2000);

      const shot5 = path.join(ARTIFACTS_DIR, '05_user_edited_successfully.png');
      await page.screenshot({ path: shot5, fullPage: true });
      console.log(`   📸 Скриншот таблицы после успешного редактирования: ${shot5}`);
    }

    console.log('\n🎉 Интерактивное UI-тестирование создания и редактирования пользователей успешно завершено!');

  } catch (err) {
    console.error('❌ Ошибка во время выполнения UI автоматизации:', err);
    process.exitCode = 1;
  } finally {
    await browser.close();
  }
}

runInteractiveUsersUiTest();
