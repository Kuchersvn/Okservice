// 1. Добавляем проверку на существование Telegram.WebApp
function sendForm(name, phone, problem) {
  if (!window.Telegram?.WebApp) {
    console.error('Telegram.WebApp не доступен');
    alert('Откройте приложение через Telegram');
    return;
  }

  const payload = {
    name: name,
    phone: phone,
    problem: problem,
    source: "webapp",
    // Добавляем timestamp для уникальности
    timestamp: Date.now()
  };

  console.log('Отправляю данные:', payload);
  
  try {
    Telegram.WebApp.sendData(JSON.stringify(payload));
    // Не закрываем сразу - даем Telegram обработать отправку
    setTimeout(() => {
      Telegram.WebApp.close();
    }, 300);
  } catch (error) {
    console.error('Ошибка отправки:', error);
    alert('Ошибка отправки: ' + error.message);
  }
}

function sendId(id) {
  if (!window.Telegram?.WebApp) {
    console.error('Telegram.WebApp не доступен');
    return;
  }
  
  console.log('Отправляю ID:', id);
  Telegram.WebApp.sendData(id.toString());
  setTimeout(() => {
    Telegram.WebApp.close();
  }, 300);
}

// 2. Инициализируем Telegram WebApp при загрузке страницы
document.addEventListener('DOMContentLoaded', function() {
  // Проверяем, запущены ли мы в Telegram
  if (window.Telegram?.WebApp) {
    const tg = Telegram.WebApp;
    tg.ready(); // Важно: сообщаем Telegram что приложение готово
    tg.expand(); // Разворачиваем на весь экран
    
    console.log('Telegram WebApp инициализирован');
    console.log('User ID:', tg.initDataUnsafe?.user?.id);
  } else {
    console.warn('Запущено вне Telegram. Для теста создан mock-объект.');
    // Мок для тестирования в браузере
    window.Telegram = {
      WebApp: {
        sendData: function(data) {
          console.log('MOCK: Данные отправлены:', data);
          alert('Тест: Данные отправлены. В Telegram они уйдут боту.');
        },
        close: function() {
          console.log('MOCK: Приложение закрыто');
        },
        ready: function() {},
        expand: function() {},
        initDataUnsafe: {}
      }
    };
  }

  // 3. Вешаем обработчик на кнопку
  const sendBtn = document.getElementById("sendBtn");
  if (sendBtn) {
    sendBtn.addEventListener("click", function() {
      const name = document.getElementById("name")?.value.trim();
      const phone = document.getElementById("phone")?.value.trim();
      const problem = document.getElementById("problem")?.value.trim();

      // Валидация
      if (!name || !phone || !problem) {
        alert('Заполните все поля!');
        return;
      }

      if (phone.length < 5) {
        alert('Введите корректный номер телефона');
        return;
      }

      console.log('Данные для отправки:', { name, phone, problem });
      sendForm(name, phone, problem);
    });
  } else {
    console.error('Кнопка #sendBtn не найдена!');
  }
});
