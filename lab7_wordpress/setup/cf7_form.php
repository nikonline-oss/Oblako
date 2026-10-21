<?php
// Создаёт форму регистрации Contact Form 7 (ЛР 7-2, задание 3) и печатает её шорткод.
// Запуск: wp eval-file /setup/cf7_form.php

$form = WPCF7_ContactForm::get_template(['title' => 'Регистрация', 'locale' => 'ru_RU']);
$props = $form->get_properties();

$props['form'] = <<<'FORM'
<label> Ваше имя
    [text* reg-name autocomplete:name placeholder "Иван Иванов"] </label>

<label> E-mail
    [email* reg-email autocomplete:email placeholder "ivanov@example.com"] </label>

<label> Группа
    [select* reg-group "ИС-21" "ИС-22" "ИС-23" "Другая"] </label>

<label> Телефон
    [tel reg-phone placeholder "+7 900 000-00-00"] </label>

[acceptance reg-accept] Согласен на обработку персональных данных [/acceptance]

[submit "Зарегистрироваться"]
FORM;

$props['mail']['subject'] = '[_site_title] Новая регистрация: [reg-name]';
$props['mail']['sender'] = '[_site_title] <wordpress@example.com>';
$props['mail']['body'] = "Имя: [reg-name]\nE-mail: [reg-email]\nГруппа: [reg-group]\nТелефон: [reg-phone]\n\n-- \nОтправлено с сайта [_site_title] ([_site_url])";
$props['mail']['recipient'] = '[_site_admin_email]';
$props['mail']['additional_headers'] = 'Reply-To: [reg-email]';
$props['mail_2']['active'] = false;

// Почтового сервера в контейнере нет: письмо не отправляем, а заявки сохраняет
// плагин Flamingo (Консоль → Flamingo → Входящие сообщения)
$props['additional_settings'] = implode("\n", [
    'skip_mail: on',
    'flamingo_name: "[reg-name]"',
    'flamingo_email: "[reg-email]"',
    'flamingo_subject: "Регистрация: [reg-name], [reg-group]"',
]);

$props['messages']['mail_sent_ok'] = 'Спасибо! Вы зарегистрированы.';

$form->set_properties($props);
$form->save();

echo $form->shortcode();
