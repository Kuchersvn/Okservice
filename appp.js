function sendForm(name, phone, problem) {
  console.log("1. Начало отправки формы");
  console.log("Данные:", { name, phone, problem });
  
  if (!window.Telegram?.WebApp) {
    console.error("2. Telegram.WebApp не найден!");
    alert("Ошибка: Откройте приложение через Telegram");
    return;
  }
  
  console.log("3. Telegram.WebApp доступен");
  const tg = Telegram.WebApp;
  
  const payload = {
    name: name,
    phone: phone,
    problem: problem,
    source: "webapp",
    timestamp: Date.now()
  };
  
  console.log("4. Отправляемый payload:", payload);
  
  try {
    console.log("5. Вызов tg.sendData()");
    tg.sendData(JSON.stringify(payload));
    
    console.log("6. Данные отправлены, закрываем приложение через 500мс");
    setTimeout(() => {
      tg.close();
      console.log("7. Приложение закрыто");
    }, 500);
    
  } catch (error) {
    console.error("8. Ошибка при отправке:", error);
    alert("Ошибка при отправке: " + error.message);
  }
}

// Инициализация
document.addEventListener('DOMContentLoaded', function() {
  console.log("DOM загружен");
  
  if (window.Telegram?.WebApp) {
    console.log("Telegram WebApp обнаружен");
    Telegram.WebApp.ready();
    Telegram.WebApp.expand();
    console.log("User ID:", Telegram.WebApp.initDataUnsafe?.user?.id);
  }
  
  const btn = document.getElementById("sendBtn");
  if (btn) {
    btn.addEventListener("click", function() {
      console.log("Кнопка нажата!");
      
      const name = document.getElementById("name")?.value.trim();
      const phone = document.getElementById("phone")?.value.trim();
      const problem = document.getElementById("problem")?.value.trim();
      
      console.log("Собранные данные:", { name, phone, problem });
      
      if (!name || !phone || !problem) {
        alert("Заполните все поля!");
        return;
      }
      
      sendForm(name, phone, problem);
    });
  }
});
