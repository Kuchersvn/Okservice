// Отправка JSON-формы в Telegram Bot
function sendForm(name, phone, problem) {
  const payload = {
    name: name,
    phone: phone,
    problem: problem,
    source: "webapp"
  };

  Telegram.WebApp.sendData(JSON.stringify(payload));
  Telegram.WebApp.close();
}

// Отправка короткого ID
function sendId(id) {
  Telegram.WebApp.sendData(id);
  Telegram.WebApp.close();
}

// Обработчик кнопки
document.getElementById("sendBtn").addEventListener("click", function() {
  const name = document.getElementById("name").value;
  const phone = document.getElementById("phone").value;
  const problem = document.getElementById("problem").value;

  sendForm(name, phone, problem);
});
