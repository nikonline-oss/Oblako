<?php
// Генерирует картинки для страниц и записей ЛР7 (вместо фото из интернета).
// Запуск: wp eval-file /setup/make_images.php  → /tmp/lab7-img/*.png

$dir = '/tmp/lab7-img';
if (!is_dir($dir)) {
    mkdir($dir, 0777, true);
}

$items = [
    'portfolio'    => [[52, 101, 164], 'PORTFOLIO'],
    'achievements' => [[214, 96, 46], 'ACHIEVEMENTS'],
    'student'      => [[46, 139, 87], 'STUDENT'],
    'schedule'     => [[123, 88, 163], 'SCHEDULE'],
    'news1'        => [[0, 128, 128], 'NEWS'],
    'news2'        => [[200, 60, 90], 'EVENTS'],
    'news3'        => [[90, 90, 200], 'TEAM'],
    'study1'       => [[30, 110, 60], 'LECTURES'],
    'study2'       => [[170, 120, 20], 'LAB WORK'],
    'study3'       => [[60, 60, 60], 'EXAMS'],
];

mt_srand(7);
foreach ($items as $name => [$rgb, $label]) {
    $w = 1200;
    $h = 630;
    $im = imagecreatetruecolor($w, $h);

    // Вертикальный градиент
    for ($y = 0; $y < $h; $y++) {
        $k = 1 - 0.45 * $y / $h;
        $c = imagecolorallocate($im, (int) ($rgb[0] * $k), (int) ($rgb[1] * $k), (int) ($rgb[2] * $k));
        imageline($im, 0, $y, $w, $y, $c);
    }

    // Полупрозрачные круги
    imagealphablending($im, true);
    for ($i = 0; $i < 9; $i++) {
        $r = mt_rand(80, 320);
        $white = imagecolorallocatealpha($im, 255, 255, 255, mt_rand(95, 115));
        imagefilledellipse($im, mt_rand(0, $w), mt_rand(0, $h), $r, $r, $white);
    }

    // Надпись: встроенный шрифт GD, увеличенный в 6 раз
    $tw = strlen($label) * imagefontwidth(5);
    $th = imagefontheight(5);
    $text = imagecreatetruecolor($tw, $th);
    imagesavealpha($text, true);
    imagefill($text, 0, 0, imagecolorallocatealpha($text, 0, 0, 0, 127));
    imagestring($text, 5, 0, 0, $label, imagecolorallocate($text, 255, 255, 255));
    $scale = 6;
    imagecopyresampled($im, $text, (int) (($w - $tw * $scale) / 2), (int) (($h - $th * $scale) / 2),
        0, 0, $tw * $scale, $th * $scale, $tw, $th);

    imagepng($im, "$dir/$name.png");
    WP_CLI::log("$dir/$name.png");
}
