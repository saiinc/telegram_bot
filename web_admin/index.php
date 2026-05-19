<?php
    
    include 'elems/init.php';
    
    if (!empty($_SESSION['auth'])) {
        function showChatCards ($link) {
            // Определяем уровень доступа
            $username = $_SESSION['username'] ?? '';
            $isAdmin = ($username === 'admin');
            if ($isAdmin) {
                // Администратор видит все чаты
                $query = "SELECT * FROM chats ORDER BY chat_id";
                $result = pg_query($link, $query) or die('Could not connect: ' . pg_last_error());
            } else {
                // Ограниченный пользователь видит только доступные чаты
                // Более безопасный вариант с подготовленным выражением
                $query = "SELECT c.* FROM chats c
                        INNER JOIN chat_access ca ON c.chat_id = ca.chat_id
                        WHERE ca.username = $1
                        ORDER BY c.chat_id";
                $result = pg_query_params($link, $query, array($username)) or die('Could not connect: ' . pg_last_error());
            }
            for ($data = []; $row = pg_fetch_array($result, null, PGSQL_ASSOC); $data[] = $row );
            $title = 'admin main page';
            
            if ($data) {
                $content = '<div class="chats-container">';
                $content .= '<h2>Список чатов</h2>';
                
                foreach ($data as $chat) {
                    $content .= '<div class="chat-card">';
                    $content .= '<div class="chat-header">';
                    $content .= '<h3>' . htmlspecialchars($chat['title']) . '</h3>';
                    $content .= '<div class="chat-id">ID: ' . htmlspecialchars($chat['chat_id']) . '</div>';
                    $content .= '</div>';
                    
                    if (!empty($chat['description'])) {
                        $content .= '<div class="chat-description">' . htmlspecialchars($chat['description']) . '</div>';
                    }
                    
                    if (!empty($chat['support_chat_id'])) {
                        $content .= '<div class="chat-support">Support chat: ' . htmlspecialchars($chat['support_chat_id']) . '</div>';
                    }
                    
                    $content .= '<div class="chat-links">';
                    $content .= '<div class="links-group">';
                    $content .= '<h4>Справка</h4>';
                    $content .= '<a href="/admin/helper.php?chat_id=' . $chat['chat_id'] . '">Helper</a> | ';
                    $content .= '<a href="/admin/str_content.php?chat_id=' . $chat['chat_id'] . '&content_type=rand_pervoe">Rand pervoe</a>';
                    $content .= '</div>';
                    
                    $content .= '<div class="links-group">';
                    $content .= '<h4>Модерация</h4>';
                    $content .= '<a href="/admin/str_content.php?chat_id=' . $chat['chat_id'] . '&content_type=delete_words">Delete words</a> | ';
                    $content .= '<a href="/admin/str_content.php?chat_id=' . $chat['chat_id'] . '&content_type=profile_words">Profile words</a> | ';
                    $content .= '<a href="/admin/str_content.php?chat_id=' . $chat['chat_id'] . '&content_type=ping_words">Ping words</a> | ';
                    $content .= '</div>';
                    
                    $content .= '<div class="links-group">';
                    $content .= '<h4>Вовлечение</h4>';
                    $content .= '<a href="/admin/str_content.php?chat_id=' . $chat['chat_id'] . '&content_type=ping_rand">Ping rand</a> | ';
                    $content .= '<a href="/admin/rp_actions.php?chat_id=' . $chat['chat_id'] . '">RP Actions</a> | ';
                    $content .= '<a href="/admin/str_content.php?chat_id=' . $chat['chat_id'] . '&content_type=goodbye">Goodbye</a>';
                    $content .= '</div>';
                    
                    $content .= '</div>'; // chat-links
                    $content .= '</div>'; // chat-card
                }
                
                $content .= '</div>'; // chats-container
            } else {
                $content = '<div class="no-chats"><h2>Нет данных</h2><p>Список чатов пуст</p></div>';
            }
            
            include 'elems/layout.php';
            
            // Free resultset
            pg_free_result($result);
        }
        showChatCards($link);
    } else {
        header('Location: /admin/login.php'); die();
    }
