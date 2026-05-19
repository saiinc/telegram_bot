<?php
    include 'elems/init.php';

    if (!empty($_SESSION['auth'])) {
        function getContent($link)
        {
            $title = 'admin add new content';

            if (isset($_GET['id'])){
                $id = $_GET['id'];
                $query = "SELECT * FROM helper WHERE id='$id'";
                $result = pg_query($link, $query) or die('Could not connect: ' . pg_last_error());
                $helper = pg_fetch_array($result, null, PGSQL_ASSOC);
                
                if ($helper) {
                    $chat_id = $helper['chat_id'];
                    // Проверяем доступ к чату
                    if (!checkChatAccess($link, $chat_id)) {
                        denyAccess();
                    }
                    $command = $helper['command'];
                    $delay = $helper['delay'];
                    $content = $helper['content'];
                
                $content = '
                <form method="POST">
                    <br>
                    chat_id: <input name="chat_id" value="' . $chat_id . '" placeholder="chat_id" style="border: none; outline: none;" readonly><br><br>
                    command:<br>
                    <input name="command" value="' . $command . '" placeholder="command"><br><br>
                    delay:<br>
                    <input name="delay" value="' . $delay . '" placeholder="delay"><br><br>
                    content:<br>
                    <textarea name="content" placeholder="content" cols="50">' . $content . '</textarea><br><br>
                    <input type="submit">
                </form>';
                } else {
                    $content = 'Данные не найдены';
                }
            } else {
                $content = 'Данные не найдены';
            }

            include 'elems/layout.php';
        }

        function editContent($link)
        {
            if (!empty($_POST['chat_id']) and !empty($_POST['command']) and !empty($_POST['delay']) and !empty($_POST['content'])) {
                $chat_id = $_POST['chat_id'];
                // Проверяем доступ к чату
                if (!checkChatAccess($link, $chat_id)) {
                    denyAccess();
                }
                $command = $_POST['command'];
                $delay = $_POST['delay'];
                $content = $_POST['content'];
                
                //$query = "SELECT COUNT(*) as count FROM helper WHERE chat_id='$chat_id' AND command='$command'";
                //$result = pg_query($link, $query) or die('Could not connect: ' . pg_last_error());
                //$isContent = pg_fetch_array($result, null, PGSQL_ASSOC)['count'];

                if (isset($_GET['id'])) {
                    $id = $_GET['id'];
                    $query = "UPDATE helper SET chat_id = '$chat_id', command = $$$command$$, delay = '$delay', content = $$$content$$ WHERE id = '$id'";
                    pg_query($link, $query) or die('Could not connect: ' . pg_last_error());
                    $_SESSION['message'] = [
                        'text' => 'Успешно отредактировано',
                        'status' => 'success'
                    ];
                    header("Location: /admin/helper.php?chat_id=$chat_id"); die();
                }

            } else {
                return '';
            }
        }

        editContent($link);
        getContent($link);
    } else {
        header('Location: /admin/login.php'); die();
    }