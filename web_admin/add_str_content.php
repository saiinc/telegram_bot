<?php
    include 'elems/init.php';

    if (!empty($_SESSION['auth'])) {
        function getContent($link)
        {
            $title = 'admin add new str_content';
            // Проверяем доступ к чату
            if (isset($_GET['chat_id'])) {
                $chat_id = $_GET['chat_id'];
                if (!checkChatAccess($link, $chat_id)) {
                    denyAccess();
                }
            }

            if (!empty($_GET['chat_id']) and !empty($_POST['content_type']) and !empty($_POST['str_content'])) {
                $chat_id = $_GET['chat_id'];
                $content_type = $_GET['content_type'];
                $value = $_POST['value'];
            } else {
                $chat_id = $_GET['chat_id'];
                $content_type = $_GET['content_type'];
                $value = '';
            }

            $content = '
            <form method="POST">
                <br>
                chat_id: <input name="chat_id" value="' . $chat_id . '" style="border: none; outline: none;" readonly><br><br>
                <input name="content_type" value="' . $content_type . '" style="border: none; outline: none;" readonly><br><br>
                <textarea name="value" placeholder="value">' . $value . '</textarea><br><br>
                <input type="submit">
            </form>';

            include 'elems/layout.php';
        }

        function addContent($link)
        {
            if (!empty($_GET['chat_id']) and !empty($_POST['content_type']) and !empty($_POST['value'])) {
                $chat_id =$_GET['chat_id'];
                // Проверяем доступ к чату
                if (!checkChatAccess($link, $chat_id)) {
                    denyAccess();
                }
                $content_type = $_POST['content_type'];
                $value = $_POST['value'];
                
                $query = "SELECT COUNT(*) as count FROM str_content WHERE chat_id='$chat_id' AND content_type='$content_type' AND value='$value'";
                $result = pg_query($link, $query) or die('Could not connect: ' . pg_last_error());
                $isContent = pg_fetch_array($result, null, PGSQL_ASSOC)['count'];

                if ($isContent) {
                    $_SESSION['message'] = [
                        'text' => 'Такая запись уже существует!',
                        'status' => 'error'
                    ];
                } else {
                    $query = "INSERT INTO str_content (chat_id, content_type, value) VALUES ('$chat_id', $$$content_type$$, $$$value$$)";
                    pg_query($link, $query) or die('Could not connect: ' . pg_last_error());

                    $_SESSION['message'] = [
                        'text' => 'Успешно добавлено',
                        'status' => 'success'
                    ];
                    
                    header("Location: /admin/str_content.php?chat_id=$chat_id&content_type=$content_type"); die();

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