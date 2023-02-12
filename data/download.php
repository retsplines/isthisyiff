<?php
$sourceFiles = json_decode(file_get_contents('safe2.json'), true);
foreach ($sourceFiles as $sourceFile) {
    $url = $sourceFile['cmd'];
    exec('curl ' . $url . ' --output assets/' . basename($url));
}
