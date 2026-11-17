let tg = window.Telegram.WebApp;
tg.expand();
tg.MainButton.textColor = "#FFFFFF";
tg.MainButton.color = "#2cab37";

// Блюда: id совпадает с id в таблице dishes в БД бота
let dishes = [
    [1, "🍲", "Борщ"], [2, "🥣", "Солянка"], [3, "🍜", "Суп с лапшой"], [4, "🥟", "Пельмени"],
    [5, "🍚", "Плов"], [6, "🍖", "Котлеты"], [7, "🥬", "Голубцы"], [8, "🥘", "Гуляш"],
    [9, "🍝", "Макароны"], [10, "🍗", "Курица"], [11, "🥔", "Картошка"], [12, "🧀", "Жюльен"]
];
let item = "";

// Рисуем кнопки с «картинками» (эмодзи) для каждого блюда
dishes.forEach(function (dish) {
    let div = document.createElement("div");
    div.className = "item";
    div.innerHTML = '<div class="img">' + dish[1] + '</div><button class="btn">' + dish[2] + '</button>';
    div.querySelector("button").addEventListener("click", function () {
        item = String(dish[0]);
        tg.MainButton.setText("Показать: " + dish[2]);
        tg.MainButton.show();
    });
    document.getElementById("list").appendChild(div);
});

// Отправляем выбранное блюдо боту
Telegram.WebApp.onEvent("mainButtonClicked", function () {
    tg.sendData(item);
});
