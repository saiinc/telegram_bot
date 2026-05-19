<?php
// generate_hash.php

if (isset($_GET['password'])) {
     $password = $_GET['password'];
     // Используем PASSWORD_DEFAULT, который в настоящее время является bcrypt
     $hash = password_hash($password, PASSWORD_DEFAULT);
     echo "Пароль: " . htmlspecialchars($password) . "<br>";
     echo "Хэш: " . htmlspecialchars($hash) . "<br><br>";
     echo "Сохраните этот хэш в вашем новом login.php или в базе данных.<br>";
} else {
     echo '<form method="GET">';
     echo 'Введите пароль для хэширования: ';
     echo '<input type="text" name="password">';
     echo '<input type="submit" value="Сгенерировать хэш">';
     echo '</form>';
}
?>