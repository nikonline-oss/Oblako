#!/bin/bash
# Установка и наполнение сайта WordPress для ЛР 7-1 и 7-2 через WP-CLI.
# Запускается в контейнере cli из ../setup.sh. Повторный запуск ничего не дублирует.
set -euo pipefail
cd /var/www/html

: "${WP_ADMIN_PASSWORD:?WP_ADMIN_PASSWORD не задан (см. .env)}"

log() { echo; echo "==> $*"; }
# Загрузки с wordpress.org иногда обрываются — пробуем до 3 раз
retry() {
  local n
  for n in 1 2 3; do
    "$@" && return 0
    echo "Не получилось, повтор ($n/3)..."
    sleep 5
  done
  return 1
}

# ===================== 7-1, I. Установка =====================
if ! wp core is-installed 2>/dev/null; then
  log "Устанавливаю WordPress ($WP_URL)"
  wp core install --url="$WP_URL" --title="$WP_TITLE" \
    --admin_user="$WP_ADMIN_USER" --admin_password="$WP_ADMIN_PASSWORD" \
    --admin_email="$WP_ADMIN_EMAIL" --skip-email
fi

# Скачивание с wordpress.org, даже если VPN/прокси подменяет DNS (см. wporg-hosts.php)
mkdir -p wp-content/mu-plugins
cp /setup/wporg-hosts.php wp-content/mu-plugins/lab7-wporg-hosts.php

log "Русский язык"
retry wp language core install ru_RU --activate

if [ "$(wp option get lab7_seeded 2>/dev/null || true)" = "1" ]; then
  log "Сайт уже наполнен — пропускаю (чтобы наполнить заново: ./setup.sh reset)"
  exit 0
fi

# От имени администратора: иначе WordPress вырежет iframe карты и <video> из контента
WP="wp --user=$WP_ADMIN_USER"

# ===================== 7-1, II. Настройки =====================
log "Настройки: индексация, часовой пояс UTC+9, формат даты, постоянные ссылки"
wp option update blogdescription "Портфолио, новости группы и всё для учёбы"
wp option update blog_public 0                # «Попросить поисковые системы не индексировать сайт»
wp option update timezone_string ''
wp option update gmt_offset 9                 # UTC+9
wp option update date_format 'd.m.Y'
wp option update time_format 'H:i'
wp option update start_of_week 1
wp rewrite structure '/%postname%/'          # .htaccess с правилами уже есть в образе wordpress

# ===================== 7-1, III. Тема =====================
log "Тема Twenty Sixteen (классическая: меню, виджеты в боковой колонке)"
retry wp theme install twentysixteen --activate
retry wp language theme install twentysixteen ru_RU || true

# ===================== 7-2. Плагины =====================
log "Плагины: Contact Form 7, Flamingo, Shortcodes Ultimate, Classic Widgets"
for plugin in contact-form-7 flamingo shortcodes-ultimate classic-widgets; do
  retry wp plugin install "$plugin" --activate
done
retry wp language plugin install --all ru_RU || true

log "Удаляю демо-контент"
for slug in hello-world sample-page; do
  for id in $(wp post list --post_type=any --name="$slug" --field=ID); do wp post delete "$id" --force; done
done

# ===================== Медиафайлы (с alt и описанием) =====================
log "Картинки в медиафайлы"
wp eval-file /setup/make_images.php
img() {  # img файл "заголовок" "alt" "описание" → ID вложения
  wp media import "/tmp/lab7-img/$1.png" --title="$2" --alt="$3" --desc="$4" --porcelain
}
I_PORTFOLIO=$(img portfolio "Портфолио" "Обложка раздела Портфолио" "Иллюстрация к странице портфолио студента")
I_ACHIEVE=$(img achievements "Достижения" "Обложка страницы Мои достижения" "Иллюстрация к списку достижений")
I_STUDENT=$(img student "Студенту" "Обложка раздела Студенту" "Иллюстрация к разделу для студентов")
I_SCHEDULE=$(img schedule "Расписание" "Обложка страницы Расписание" "Иллюстрация к расписанию занятий")
I_NEWS1=$(img news1 "Новости" "Иллюстрация к новости о начале семестра" "Картинка к записи рубрики Новости группы")
I_NEWS2=$(img news2 "Мероприятия" "Иллюстрация к новости о мероприятии" "Картинка к записи рубрики Новости группы")
I_NEWS3=$(img news3 "Команда" "Иллюстрация к новости о старосте группы" "Картинка к записи рубрики Новости группы")
I_STUDY1=$(img study1 "Лекции" "Иллюстрация к записи о лекциях" "Картинка к записи рубрики Учёба")
I_STUDY2=$(img study2 "Лабораторные" "Иллюстрация к записи о лабораторных работах" "Картинка к записи рубрики Учёба")
I_STUDY3=$(img study3 "Экзамены" "Иллюстрация к записи об экзаменах" "Картинка к записи рубрики Учёба")

# ===================== Блоки редактора =====================
url_of() { wp eval "echo wp_get_attachment_url($1);"; }
h() {  # h уровень "текст"
  if [ "$1" = 2 ]; then
    printf '<!-- wp:heading -->\n<h2 class="wp-block-heading">%s</h2>\n<!-- /wp:heading -->\n\n' "$2"
  else
    printf '<!-- wp:heading {"level":%s} -->\n<h%s class="wp-block-heading">%s</h%s>\n<!-- /wp:heading -->\n\n' "$1" "$1" "$2" "$1"
  fi
}
p() { printf '<!-- wp:paragraph -->\n<p>%s</p>\n<!-- /wp:paragraph -->\n\n' "$1"; }
image() {  # image ID "alt"
  printf '<!-- wp:image {"id":%s,"sizeSlug":"large","linkDestination":"none"} -->\n<figure class="wp-block-image size-large"><img src="%s" alt="%s" class="wp-image-%s"/></figure>\n<!-- /wp:image -->\n\n' \
    "$1" "$(url_of "$1")" "$2" "$1"
}
ul() {  # ul "пункт" "пункт" ...
  printf '<!-- wp:list -->\n<ul class="wp-block-list">'
  for item in "$@"; do printf '<!-- wp:list-item -->\n<li>%s</li>\n<!-- /wp:list-item -->' "$item"; done
  printf '</ul>\n<!-- /wp:list -->\n\n'
}
table() {  # table "заг1|заг2" "яч|яч" ...
  local head=$1; shift
  printf '<!-- wp:table {"hasFixedLayout":true} -->\n<figure class="wp-block-table"><table class="has-fixed-layout"><thead><tr>'
  IFS='|' read -ra cols <<< "$head"; for c in "${cols[@]}"; do printf '<th>%s</th>' "$c"; done
  printf '</tr></thead><tbody>'
  for row in "$@"; do
    printf '<tr>'; IFS='|' read -ra cols <<< "$row"; for c in "${cols[@]}"; do printf '<td>%s</td>' "$c"; done; printf '</tr>'
  done
  printf '</tbody></table></figure>\n<!-- /wp:table -->\n\n'
}
VIDEO_URL="https://interactive-examples.mdn.mozilla.net/media/cc0-videos/flower.mp4"
video() { printf '<!-- wp:video -->\n<figure class="wp-block-video"><video controls src="%s"></video><figcaption class="wp-element-caption">%s</figcaption></figure>\n<!-- /wp:video -->\n\n' "$VIDEO_URL" "$1"; }
html() { printf '<!-- wp:html -->\n%s\n<!-- /wp:html -->\n\n' "$1"; }
shortcode() { printf '<!-- wp:shortcode -->\n%s\n<!-- /wp:shortcode -->\n\n' "$1"; }

page() {  # page "заголовок" "slug" "контент" [родитель] → ID
  $WP post create --post_type=page --post_status=publish --post_title="$1" --post_name="$2" \
    --post_content="$3" --post_parent="${4:-0}" --porcelain
}
post() {  # post "заголовок" "slug" "контент" рубрика картинка "метки" "дата" → ID
  local id
  id=$($WP post create --post_type=post --post_status=publish --post_title="$1" --post_name="$2" \
    --post_content="$3" --post_category="$4" --tags_input="$6" --post_date="$7" --porcelain)
  wp post meta set "$id" _thumbnail_id "$5" >/dev/null
  echo "$id"
}

# ===================== 7-1, IV / 7-2. Страницы =====================
log "Страницы (Портфолио → Мои достижения, Студенту → Расписание)"
SU_TABS='[su_tabs]
[su_tab title="Программирование"]Python, Django, JavaScript, SQL[/su_tab]
[su_tab title="Облака"]Docker, Docker Swarm, Render, MongoDB[/su_tab]
[su_tab title="Инструменты"]Git, GitHub, Linux, WordPress[/su_tab]
[/su_tabs]'
SU_SPOILER='[su_spoiler title="Подробнее о проектах" style="fancy" icon="arrow"]CRM-система на Django: учёт нарядов, сотрудников, товаров; работа с Dropbox API; развёртывание в Docker и на Render.[/su_spoiler]'
SU_NOTE='[su_note note_color="#fff3cd" text_color="#664d03"]Расписание может меняться — проверяйте страницу перед занятиями.[/su_note]'
SU_BUTTON='[su_button url="#" style="flat" background="#2271b1" size="6" icon="icon: calendar"]Скачать расписание[/su_button]'

P_PORTFOLIO=$(page "Портфолио" "portfolio" "$(
  h 2 "Обо мне"
  image "$I_PORTFOLIO" "Обложка раздела Портфолио"
  p "Студент направления «Информационные системы и технологии». Занимаюсь веб-разработкой и облачными технологиями."
  h 3 "Навыки"
  shortcode "$SU_TABS"
  h 3 "Проекты"
  table "Проект|Технологии|Год" "CRM-система|Django, PostgreSQL, Docker|2025" "Swarm-ферма|Docker Swarm, PostgreSQL|2026" "Сайт студента|WordPress|2026"
  shortcode "$SU_SPOILER"
)")
P_ACHIEVE=$(page "Мои достижения" "achievements" "$(
  h 2 "Мои достижения"
  image "$I_ACHIEVE" "Обложка страницы Мои достижения"
  table "Дата|Достижение|Уровень" "05.2025|Победа в хакатоне колледжа|Колледж" "11.2025|Сертификат Docker Fundamentals|Онлайн-курс" "03.2026|Доклад на студенческой конференции|Региональный"
  h 3 "Видео с конференции"
  video "Фрагмент выступления"
)" "$P_PORTFOLIO")
MAP_IFRAME="<iframe src=\"https://yandex.ru/map-widget/v1/?ll=${MAP_LL}&amp;z=16&amp;pt=${MAP_LL},pm2rdm\" width=\"100%\" height=\"400\" frameborder=\"0\" allowfullscreen=\"true\" style=\"position:relative;\"></iframe>"
P_STUDENT=$(page "Студенту" "student" "$(
  h 2 "Полезная информация"
  image "$I_STUDENT" "Обложка раздела Студенту"
  ul "Расписание занятий — в подразделе «Расписание»" "Новости группы — в рубрике «Новости группы»" "Материалы к занятиям — в рубрике «Учёба»"
  h 3 "Как нас найти"
  p "Интерактивная Яндекс.Карта с расположением учебного корпуса:"
  html "$MAP_IFRAME"
  h 3 "Контакты"
  table "Кабинет|Назначение|Часы работы" "101|Учебная часть|09:00–17:00" "214|Компьютерный класс|08:30–18:00" "305|Библиотека|10:00–16:00"
)")
P_SCHEDULE=$(page "Расписание" "schedule" "$(
  h 2 "Расписание занятий"
  shortcode "$SU_NOTE"
  image "$I_SCHEDULE" "Обложка страницы Расписание"
  h 3 "Неделя 1"
  table "День|1 пара|2 пара|3 пара" "Понедельник|Облачные технологии|Базы данных|Физкультура" "Вторник|Веб-программирование|Английский язык|—" "Среда|Облачные технологии (лаб.)|Базы данных (лаб.)|Математика" "Четверг|Веб-программирование (лаб.)|Экономика|—" "Пятница|Проектный практикум|Проектный практикум|—"
  shortcode "$SU_BUTTON"
)" "$P_STUDENT")

# ===================== 7-2, задание 1. Рубрики и записи =====================
log "Рубрики и записи (2 × 3)"
C_NEWS=$(wp term create category "Новости группы" --slug=news --description="Новости и события нашей группы" --porcelain)
C_STUDY=$(wp term create category "Учёба" --slug=study --description="Лекции, лабораторные и экзамены" --porcelain)
UNCAT=$(wp option get default_category)
wp option update default_category "$C_NEWS"
wp term delete category "$UNCAT" || true

post "Начался новый семестр" "semester-start" "$(
  h 2 "Добро пожаловать в 7 семестр!"
  image "$I_NEWS1" "Иллюстрация к новости о начале семестра"
  p "С 1 сентября начались занятия. В этом семестре у нас новые дисциплины: облачные технологии и проектный практикум."
  h 3 "Новые дисциплины"
  table "Дисциплина|Преподаватель|Форма контроля" "Облачные технологии|Петров П. П.|Экзамен" "Проектный практикум|Сидорова А. В.|Зачёт"
)" "$C_NEWS" "$I_NEWS1" "семестр, новости" "2026-09-01 09:00:00" >/dev/null

post "День открытых дверей" "open-day" "$(
  h 2 "Приглашаем на день открытых дверей"
  image "$I_NEWS2" "Иллюстрация к новости о мероприятии"
  p "Студенты группы покажут свои проекты: CRM-систему, Swarm-ферму и сайт на WordPress."
  h 3 "Видеоприглашение"
  video "Видео о мероприятии"
  h 4 "Программа"
  ul "10:00 — экскурсия по колледжу" "11:00 — презентации проектов" "12:30 — ответы на вопросы"
)" "$C_NEWS" "$I_NEWS2" "мероприятия, проекты" "2026-09-20 12:00:00" >/dev/null

post "Выбран староста группы" "group-leader" "$(
  h 2 "Итоги голосования"
  image "$I_NEWS3" "Иллюстрация к новости о старосте группы"
  table "Кандидат|Голосов" "Иванов И.|14" "Петрова М.|9" "Сидоров А.|3"
  p "Поздравляем нового старосту! Все вопросы по расписанию — к нему."
)" "$C_NEWS" "$I_NEWS3" "группа, новости" "2026-10-02 15:30:00" >/dev/null

post "Конспект лекции: контейнеризация" "lecture-containers" "$(
  h 2 "Что такое контейнер"
  image "$I_STUDY1" "Иллюстрация к записи о лекциях"
  p "Контейнер — изолированный процесс со своей файловой системой, сетью и ограничениями ресурсов."
  h 3 "Контейнер и виртуальная машина"
  table "Критерий|Контейнер|Виртуальная машина" "Запуск|Секунды|Минуты" "Размер образа|Мегабайты|Гигабайты" "Изоляция|Процессы ядра|Полная ОС"
  h 3 "Видео к лекции"
  video "Короткое видео к лекции"
)" "$C_STUDY" "$I_STUDY1" "docker, лекции" "2026-09-10 10:00:00" >/dev/null

post "Лабораторные работы: сроки сдачи" "lab-deadlines" "$(
  h 2 "Сроки сдачи лабораторных"
  image "$I_STUDY2" "Иллюстрация к записи о лабораторных работах"
  table "№|Тема|Срок" "1|Git|15.09" "2|Docker|29.09" "3|Docker Swarm|13.10" "4|Dropbox API|27.10" "5|PaaS|10.11" "6|MongoDB|24.11" "7|WordPress|08.12"
  h 3 "Как сдавать"
  ul "Показать работающий проект" "Ответить на контрольные вопросы" "Сдать отчёт"
)" "$C_STUDY" "$I_STUDY2" "лабораторные, сроки" "2026-09-15 09:00:00" >/dev/null

post "Подготовка к экзамену" "exam-preparation" "$(
  h 2 "Экзамен по облачным технологиям"
  image "$I_STUDY3" "Иллюстрация к записи об экзаменах"
  h 3 "Темы"
  ul "Модели облачных сервисов: IaaS, PaaS, SaaS" "Контейнеризация и оркестрация" "NoSQL базы данных" "CMS и их развёртывание"
  h 4 "Консультации"
  table "Дата|Время|Аудитория" "20.12|14:00|214" "24.12|10:00|305"
)" "$C_STUDY" "$I_STUDY3" "экзамен, учёба" "2026-10-15 18:00:00" >/dev/null

# ===================== 7-2, задание 3. Форма регистрации в боковой колонке =====================
log "Форма регистрации Contact Form 7 → виджет боковой колонки"
CF7_SHORTCODE=$(wp eval-file /setup/cf7_form.php)
wp widget reset sidebar-1
wp widget add text sidebar-1 1 --title="Регистрация" --text="$CF7_SHORTCODE"
wp widget add search sidebar-1 2 --title="Поиск"
wp widget add categories sidebar-1 3 --title="Рубрики"
wp widget add recent-posts sidebar-1 4 --title="Свежие записи" --number=5
wp widget add calendar sidebar-1 5 --title="Календарь"

# ===================== 7-1, IV / 7-2, задание 5. Выпадающее меню =====================
log "Главное меню с выпадающими пунктами"
MENU=$(wp menu create "Главное меню" --porcelain)
wp menu item add-custom "$MENU" "Главная" "$WP_URL/" >/dev/null
M_PORTFOLIO=$(wp menu item add-post "$MENU" "$P_PORTFOLIO" --porcelain)
wp menu item add-post "$MENU" "$P_ACHIEVE" --parent-id="$M_PORTFOLIO" >/dev/null
M_STUDENT=$(wp menu item add-post "$MENU" "$P_STUDENT" --porcelain)
wp menu item add-post "$MENU" "$P_SCHEDULE" --parent-id="$M_STUDENT" >/dev/null
M_BLOG=$(wp menu item add-custom "$MENU" "Рубрики" "#" --porcelain)
wp menu item add-term "$MENU" category "$C_NEWS" --parent-id="$M_BLOG" >/dev/null
wp menu item add-term "$MENU" category "$C_STUDY" --parent-id="$M_BLOG" >/dev/null
wp menu location assign "$MENU" primary

wp option update lab7_seeded 1
log "Готово: $WP_URL  (админка: $WP_URL/wp-admin/)"
