<?php
    include 'elems/init.php';

    if (!empty($_SESSION['auth'])) {
        function getContent($link)
        {
            $title = 'admin add new content';
            if (!empty($_GET['chat_id']) and !empty($_POST['command']) and !empty($_POST['delay']) and !empty($_POST['content'])) {
                $chat_id = $_GET['chat_id'];
                // Проверяем доступ к чату
                if (!checkChatAccess($link, $chat_id)) {
                    denyAccess();
                }
                $command = $_POST['command'];
                $delay = $_POST['delay'];
                $content = $_POST['content'];
            } else {
                $chat_id = $_GET['chat_id'];
                $command = '';
                $delay = '';
                $content = '';
            }

            $content = '
            <form method="POST">
                <br>
                chat_id: <input name="chat_id" value="' . $chat_id . '" style="border: none; outline: none;" readonly><br><br>
                <input name="command" value="' . $command . '" placeholder="command"><br><br>
                <input name="delay" value="' . $delay . '" placeholder="delay"><br><br>
                <textarea name="content" placeholder="content">' . $content . '</textarea><br><br>
                <input type="submit">
            </form>';

            include 'elems/layout.php';
        }

        function addContent($link)
        {
            if (!empty($_GET['chat_id']) and !empty($_POST['command']) and !empty($_POST['delay']) and !empty($_POST['content'])) {
                $chat_id =$_GET['chat_id'];
                // Проверяем доступ к чату
                if (!checkChatAccess($link, $chat_id)) {
                    denyAccess();
                }
                $command = $_POST['command'];
                $delay = $_POST['delay'];
                $content = $_POST['content'];
                
                $query = "SELECT COUNT(*) as count FROM helper WHERE chat_id='$chat_id' AND command='$command'";
                $result = pg_query($link, $query) or die('Could not connect: ' . pg_last_error());
                $isContent = pg_fetch_array($result, null, PGSQL_ASSOC)['count'];

                if ($isContent) {
                    $_SESSION['message'] = [
                        'text' => 'Такая команда уже существует!',
                        'status' => 'error'
                    ];
                } else {
                    $query = "INSERT INTO helper (chat_id, command, delay, content) VALUES ('$chat_id', $$$command$$, '$delay', $$$content$$)";
                    pg_query($link, $query) or die('Could not connect: ' . pg_last_error());

                    $_SESSION['message'] = [
                        'text' => 'Успешно добавлено',
                        'status' => 'success'
                    ];
                    
                    header("Location: /admin/helper.php?chat_id=$chat_id"); die();

                }
            } else {
                return '';
            }
        }

        addContent($link);
        getContent($link);
    } else {
        header('Location: /admin/login.php'); die();
    }