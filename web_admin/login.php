<?php

    include 'elems/init.php';

    if (isset($_POST['password'])) {
        // Получаем все хэши из таблицы password_hash
        $query = "SELECT username, hash FROM password_hash";
        $result = pg_query($link, $query) or die('Could not connect: ' . pg_last_error());
        
        $isValid = false;
        while ($row = pg_fetch_array($result, null, PGSQL_ASSOC)) {
            if (password_verify($_POST['password'], $row['hash'])) {
                $isValid = true;
                
                // Добавляем сохранение имени пользователя в сессию
                $_SESSION['username'] = $row['username'];
                break;
            }
        }
        
        if ($isValid) {
            $_SESSION['auth'] = true;
            session_regenerate_id(true); // Защита от session fixation
            header('Location: /admin/');
            die();
        }
    }
    
    $title = 'Login';
    $content = '<div class="login-form-container">
            <form method="POST">
                <label for="password">Введите пароль</label>
                <input type="password" name="password" id="password">
                <input value="Вход" type="submit">
            </form>
        </div>';
    
    include 'elems/layout.php';
?>