<?php
/**
 * Plugin Name: ЛР7 — загрузки с wordpress.org за VPN/прокси
 * Description: Если DNS отдаёт для wordpress.org «служебные» адреса (VPN/прокси в режиме
 * fake-IP, диапазон 198.18.0.0/15), WordPress отказывается скачивать переводы, темы и
 * плагины («A valid URL was not provided»). Разрешаем это только для доменов wordpress.org;
 * для остальных адресов защита WordPress работает как обычно.
 */

add_filter('http_request_host_is_external', function ($is_external, $host) {
    return $is_external || $host === 'wordpress.org' || str_ends_with($host, '.wordpress.org');
}, 10, 2);
