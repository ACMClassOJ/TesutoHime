<?php
$dir = 'data_directory';
$allowed_exts = array("gif", "jpg", "jpeg", "png");
$temp = explode(".", $_FILES["file"]["name"]);
$ext = end($temp);

// if (!(($_FILES["file"]["type"] == "image/gif")
// || ($_FILES["file"]["type"] == "image/jpeg")
// || ($_FILES["file"]["type"] == "image/jpg")
// || ($_FILES["file"]["type"] == "image/pjpeg")
// || ($_FILES["file"]["type"] == "image/x-png")
// || ($_FILES["file"]["type"] == "image/png")))
// {
//     echo "非图片类型！";
//     die();
// }

if($_FILES["file"]["size"] > 10240000)
{
    echo "-500";
    die();
}

if(!in_array($ext, $allowed_exts))
{
    echo "-501";
    die();
}

// echo "From upload.php: <br>";
// echo "文件名: " . $_FILES["file"]["name"] . "<br>";
// echo "文件类型: " . $ext . "<br>";
// echo "文件大小: " . ($_FILES["file"]["size"] / 1024) . " KB <br>";

if (!move_uploaded_file($_FILES['file']['tmp_name'], $dir . $_FILES["file"]["name"])) 
{
    echo "-502";
    die();
}
else
    echo "0";
?>