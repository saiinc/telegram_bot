<?php

    error_reporting(E_ALL);
    ini_set('display_errors', 'on');

    session_start();
    
    // Читаем учетные данные из переменных окружения
    $host = $_ENV['DB_HOST'] ?? getenv('DB_HOST');
    $port = $_ENV['DB_PORT'] ?? getenv('DB_PORT');
    $user = $_ENV['DB_USER'] ?? getenv('DB_USER');
    $password = $_ENV['DB_PASSWORD'] ?? getenv('DB_PASSWORD');
    $dbname = $_ENV['DB_NAME'] ?? getenv('DB_NAME');

    // Проверяем, что все переменные установлены
    if (!$host || !$port || !$user || !$password || !$dbname) {
		die('Не все переменные окружения установлены');
    }
    
    $link = pg_connect("host=$host port=$port dbname=$dbname user=$user password=$password");
    pg_query($link, "SET NAMES 'utf8'");

    // Функция проверки доступа к чату
    function checkChatAccess($link, $chat_id) {
      $username = $_SESSION['username'] ?? '';
    
      // Администратор имеет доступ ко всем чатам
      if ($username === 'admin') {
        return true;
      }
    
      // Проверяем доступ для ограниченного пользователя
      $query = "SELECT COUNT(*) FROM chat_access WHERE username = $1 AND chat_id = $2";
      $result = pg_query_params($link, $query, array($username, $chat_id));
   
      if (!$result) {
        return false;
      }
   
      $row = pg_fetch_array($result, null, PGSQL_NUM);
      return $row[0] > 0;
    }
   
    // Функция для безопасного перенаправления с сообщением об ошибке
    function denyAccess($message = 'Доступ к этому чату запрещен') {
      $_SESSION['message'] = [
          'text' => $message,
          'status' => 'error'
      ];
      header('Location: /admin/');
      die();
    }