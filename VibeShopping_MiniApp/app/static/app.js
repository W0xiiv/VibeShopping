const tg = window.Telegram?.WebApp;
tg?.ready();
tg?.expand();

const $ = (id) => document.getElementById(id);
const photoInput = $("photo");
let selectedFile = null;

const user = tg?.initDataUnsafe?.user;
if (user?.first_name) $("avatar").textContent = user.first_name.slice(0,1).toUpperCase();

function toast(message) {
  $("toast").textContent = message;
  $("toast").hidden = false;
  setTimeout(() => $("toast").hidden = true, 3200);
}

$("choose").addEventListener("click", () => photoInput.click());
photoInput.addEventListener("change", () => {
  const file = photoInput.files?.[0];
  if (!file) return;
  if (!["image/jpeg","image/png","image/webp"].includes(file.type)) {
    toast("Выбери изображение JPG, PNG или WEBP."); return;
  }
  if (file.size > 8 * 1024 * 1024) {
    toast("Файл должен быть меньше 8 МБ."); return;
  }
  selectedFile = file;
  $("preview").src = URL.createObjectURL(file);
  $("preview").hidden = false;
  $("analyze").hidden = false;
  $("choose").textContent = "Выбрать другое фото";
  $("results").hidden = true;
});

$("analyze").addEventListener("click", async () => {
  if (!selectedFile) return;
  if (!tg?.initData) {
    toast("Открой приложение через Telegram, чтобы подтвердить вход.");
    return;
  }
  $("loading").hidden = false;
  $("analyze").disabled = true;
  $("analyze").textContent = "Анализируем…";
  const form = new FormData();
  form.append("photo", selectedFile);
  try {
    const response = await fetch("/api/analyze", {
      method: "POST",
      headers: {"X-Telegram-Init-Data": tg.initData},
      body: form
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || "Ошибка обработки");
    $("productName").textContent = data.name;
    $("category").textContent = data.category;
    $("features").replaceChildren(...(data.features || []).map(x => {
      const el = document.createElement("span"); el.className = "feature"; el.textContent = x; return el;
    }));
    $("queries").replaceChildren(...(data.queries || []).map(x => {
      const el = document.createElement("div"); el.className = "query"; el.textContent = "• " + x; return el;
    }));
    const labels = {
      "Wildberries": ["WB", "Фиолетовый маркетплейс"],
      "Ozon": ["O", "Синий маркетплейс"],
      "Яндекс Маркет": ["Я", "Маркетплейс Яндекса"]
    };
    $("marketplaces").replaceChildren(...Object.entries(data.links).map(([name,url]) => {
      const a = document.createElement("a"); a.className = "market"; a.href = url; a.target = "_blank"; a.rel = "noopener";
      const left = document.createElement("div");
      const title = document.createElement("div"); title.textContent = name;
      const sub = document.createElement("small"); sub.textContent = labels[name]?.[1] || "Поиск аналогов";
      left.append(title, sub);
      const arrow = document.createElement("span"); arrow.className = "go"; arrow.textContent = "↗";
      a.append(left, arrow); return a;
    }));
    $("note").textContent = (data.confidence_note || "") + " Сейчас приложение открывает поиск на маркетплейсах. Цены, рейтинг и отзывы ещё не загружаются автоматически.";
    $("results").hidden = false;
    $("results").scrollIntoView({behavior:"smooth", block:"start"});
  } catch (err) {
    toast(err.message || "Не удалось обработать фото.");
  } finally {
    $("loading").hidden = true;
    $("analyze").disabled = false;
    $("analyze").textContent = "Найти аналоги";
  }
});

$("again").addEventListener("click", () => {
  selectedFile = null;
  photoInput.value = "";
  $("preview").hidden = true;
  $("analyze").hidden = true;
  $("choose").textContent = "＋ Выбрать фотографию";
  $("results").hidden = true;
  window.scrollTo({top:0,behavior:"smooth"});
});
