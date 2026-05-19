<?php
    
    include 'elems/init.php';
    
    if (!empty($_SESSION['auth'])) {
        function showHelper($link)
        {
            $title = 'admin helper page';
            if (isset($_GET['chat_id'])) {
                $chat_id = $_GET['chat_id'];
                // Проверяем доступ к чату
                if (!checkChatAccess($link, $chat_id)) {
                    denyAccess();
                }
                $query = "SELECT * FROM helper WHERE chat_id='$chat_id' ORDER BY command";
                $result = pg_query($link, $query) or die('Could not connect: ' . pg_last_error());
                for ($data = []; $row = pg_fetch_array($result, null, PGSQL_ASSOC); $data[] = $row );
                if ($data) {
                    $content = '<br><a href="/admin/">К списку чатов</a><br><br>                    <a href="/admin/add_helper.php?chat_id=' . $chat_id . '">Добавить новую запись</a><br><br>                    chat_id ' . $chat_id . '                    <table>                    <tr>                        <th>command</th>                        <th>delay</th>                        <th>content</th>                        <th>edit</th>                        <th>delete</th>                    </tr>';
                    foreach ($data as $helper) {
                        $content .= "<tr>\n                        <td>{$helper['command']}</td>\n                        <td>{$helper['delay']}</td>\n                        <td>{$helper['content']}</td>\n                        <td><a href=\"/admin/edit_helper.php?id={$helper['id']}\">edit</a></td>\n                        <td><a href=\"?delete={$helper['id']}&chat_id={$chat_id}\">delete</a></td>\n                    </tr>";
                    }
                    $content .='</table>';
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
                $query = "DELETE FROM helper WHERE id=$id";
                pg_query($link, $query) or die('Could not connect: ' . pg_last_error());
                $_SESSION['message'] = [
                    'text' => 'Запись удалена',
                    'status' => 'success'
                ];
                header("Location: /admin/helper.php?chat_id=$chat_id"); die();
            }  
        } 
        deletePage($link);

        showHelper($link);
    } else {
        header('Location: /admin/login.php'); die();
    }

