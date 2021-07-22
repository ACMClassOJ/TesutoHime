<?php
$dir = 'data_directory';
$id = basename($_FILES['file']['name'], '.zip');
if (!preg_match('/^\d+$/', $id)) {
    echo "Possible file upload attack!\n";
    die();
}
if (!move_uploaded_file($_FILES['file']['tmp_name'], $dir . $id . '.zip')) {
    echo "System Error!\n";
    die();
}
if (!file_put_contents($dir . $id . '.timestamp', time())){
    echo "System Error!\n";
    die();
}
echo "File is valid, and was successfully uploaded.\n";
?>