// Адаптированный для твоего HTML
async function sendRequest() {
  const name = document.getElementById('name').value.trim();
  const phone = document.getElementById('phone').value.trim();
  const message = document.getElementById('message').value.trim();

  console.log("1. Начало отправки формы");
  console.log("Данные:", { name, phone, message });

  // Валидация
  if (!name) {
    showNotification("⚠️ Введите ваше имя", "error");
    document.getElementById('name').focus();
    return;
  }

  if (!phone) {
    showNotification("⚠️ Введите номер телефона", "error");
    document.getElementById('phone').focus();
    return;
  }

  // Проверка телефона
  const phoneRegex = /^[\d\s\-\+\(\)]+$/;
  if (!phoneRegex.test(phone) || phone.replace(/\D/g, '').length < 10) {
    showNotification("⚠️ Введите корректный номер телефона", "error");
    document.getElementById('phone').focus();
    return;
  }

  if (!message) {
    showNotification("⚠️ Опишите проблему", "error");
    document.getElementById('message').focus();
    return;
  }

  console.log("2. Данные валидны, отправляем...");

  try {
    // Показываем статус отправки
    showNotification("⏳ Отправка заявки...", "info");

    const res = await fetch("/send_request", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name, phone, message })
    });

    console.log("3. Ответ сервера:", res.status);

    const result = await res.json().catch(() => ({ status: 'error' }));

    if (res.ok && result.status === "success") {
      console.log("✅ Заявка успешно отправлена!");
      showNotification("✅ Заявка успешно отправлена! Мы скоро свяжемся с вами.", "success");
      
      // Очищаем форму
      document.getElementById('name').value = "";
      document.getElementById('phone').value = "";
      document.getElementById('message').value = "";
      
      // Автоскрытие уведомления через 5 секунд
      setTimeout(() => {
        const notif = document.getElementById("notification");
        notif.classList.remove("show");
      }, 5000);
      
    } else {
      console.error("❌ Ошибка от сервера:", result);
      showNotification("❌ Ошибка при отправке. Попробуйте позже.", "error");
    }
  } catch (error) {
    console.error("❌ Ошибка сети:", error);
    showNotification("⚠️ Ошибка соединения с сервером.", "error");
  }
}

// Показ уведомления
function showNotification(text, type) {
  const notif = document.getElementById("notification");
  notif.textContent = text;
  
  // Устанавливаем цвет в зависимости от типа
  if (type === "error") {
    notif.style.background = "linear-gradient(90deg, #ff4d4d, #000)";
  } else if (type === "success") {
    notif.style.background = "linear-gradient(90deg, #00c851, #000)";
  } else if (type === "info") {
    notif.style.background = "linear-gradient(90deg, #33b5e5, #000)";
  }
  
  notif.classList.add("show");

  // Автоскрытие только для ошибок/успеха
  if (type !== "info") {
    setTimeout(() => {
      notif.classList.remove("show");
    }, 3000);
  }
}

// Форматирование телефона (маска ввода)
function formatPhoneInput() {
  const phoneInput = document.getElementById('phone');
  
  phoneInput.addEventListener('input', function(e) {
    let value = e.target.value.replace(/\D/g, '');
    
    if (value.length === 0) {
      e.target.value = '';
      return;
    }
    
    // Форматирование российского номера
    if (value.length <= 1) {
      e.target.value = '+7 (' + value;
    } else if (value.length <= 4) {
      e.target.value = '+7 (' + value.substring(1, 4);
    } else if (value.length <= 7) {
      e.target.value = '+7 (' + value.substring(1, 4) + ') ' + value.substring(4, 7);
    } else if (value.length <= 9) {
      e.target.value = '+7 (' + value.substring(1, 4) + ') ' + value.substring(4, 7) + '-' + value.substring(7, 9);
    } else {
      e.target.value = '+7 (' + value.substring(1, 4) + ') ' + value.substring(4, 7) + '-' + value.substring(7, 9) + '-' + value.substring(9, 11);
    }
  });
}

// Автозаполнение для теста (только на localhost)
function autoFillTestData() {
  if (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') {
    console.log("🔧 Тестовый режим: автозаполнение формы");
    document.getElementById('name').value = "Иван Иванов";
    document.getElementById('phone').value = "+7 (999) 123-45-67";
    document.getElementById('message').value = "Тестовая заявка с сайта. Ноутбук не включается.";
  }
}

// Инициализация при загрузке страницы
document.addEventListener('DOMContentLoaded', function() {
  console.log("🚀 OK Service сайт загружен");
  
  // Настройка маски телефона
  formatPhoneInput();
  
  // Автозаполнение для теста
  autoFillTestData();
  
  // Логируем все события формы
  const formInputs = document.querySelectorAll('.contact-form input, .contact-form textarea');
  formInputs.forEach(input => {
    input.addEventListener('focus', function() {
      console.log(`📝 Фокус на поле: ${this.id}`);
    });
    
    input.addEventListener('blur', function() {
      console.log(`📝 Уход с поля: ${this.id}, значение: ${this.value}`);
    });
  });
  
  // Обработчик для кнопки отправки
  const sendBtn = document.querySelector('.contact-form button');
  if (sendBtn) {
    sendBtn.addEventListener('click', function(e) {
      e.preventDefault();
      console.log("🟢 Кнопка 'Отправить заявку' нажата");
      sendRequest();
    });
  }
  
  // Также обрабатываем отправку по Enter в поле сообщения
  document.getElementById('message').addEventListener('keypress', function(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      console.log("↵ Отправка по Enter");
      sendRequest();
    }
  });
});
