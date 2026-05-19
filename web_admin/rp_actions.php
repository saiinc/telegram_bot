<?php
    
    include 'elems/init.php';
    
    if (!empty($_SESSION['auth'])) {
        function showRpActions($link)
        {
            $title = 'admin helper page';
            if (isset($_GET['chat_id'])) {
                $chat_id = $_GET['chat_id'];
                // Проверяем доступ к чату
                if (!checkChatAccess($link, $chat_id)) {
                    denyAccess();
                }
                $query = "SELECT * FROM rp_actions WHERE chat_id='$chat_id' ORDER BY action";
                $result = pg_query($link, $query) or die('Could not connect: ' . pg_last_error());
                for ($data = []; $row = pg_fetch_array($result, null, PGSQL_ASSOC); $data[] = $row);
                if ($data) {
                    $content = '<br><a href="/admin/">К списку чатов</a><br><br>\n                <a href="/admin/add_rp_actions.php?chat_id=' . $chat_id . '">Добавить новую запись</a><br><br>\n                chat_id ' . $chat_id . '\n                <table>\n                <tr>\n                    <th>action</th>\n                    <th>reaction</th>\n                    <th>edit</th>\n                    <th>delete</th>\n                </tr>';
                    foreach ($data as $rp_action) {
                        $content .= "<tr>\n                    <td>{$rp_action['action']}</td>\n                    <td>{$rp_action['reaction']}</td>\n                    <td><a href=\"/admin/edit_rp_actions.php?id={$rp_action['id']}\">edit</a></td>\n                    <td><a href=\"?delete={$rp_action['id']}&chat_id={$chat_id}\">delete</a></td>\n                </tr>";
                    }
                    $content .= '</table>';
                } else {
                    $content = '<br><a href="/admin/">К списку чатов</a><br><br>Данные не найдены<br><br>';
                }
                
                include 'elems/layout.php';
                
                // Free resultset
                pg_free_result($result);
                
                // Closing connection
                //pg_close($dbconn);
            } else {
                $content = 'Данные не найдены';
            }
        }
        
        function deletePage($link)
        {
            if (isset($_GET['delete'])) {
                $id = $_GET['delete'];
                $chat_id = $_GET['chat_id'];
                // Проверяем доступ к чату
                if (!checkChatAccess($link, $chat_id)) {
                    denyAccess();
                }
                $query = "DELETE FROM rp_actions WHERE id=$id";
                pg_query($link, $query) or die('Could not connect: ' . pg_last_error());
                $_SESSION['message'] = [
                    'text' => 'Запись удалена',
                    'status' => 'success'
                ];
                header("Location: /admin/rp_actions.php?chat_id=$chat_id");
                die();
            }  
        } 
        deletePage($link);
        
        showRpActions($link);
    } else {
        header('Location: /admin/login.php');
        die();
    }
