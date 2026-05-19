<?php
    include 'elems/init.php';

    if (!empty($_SESSION['auth'])) {
        function getContent($link)
        {
            $title = 'admin add new rp actions';
            // Проверяем доступ к чату
            if (isset($_GET['chat_id'])) {
                $chat_id = $_GET['chat_id'];
                if (!checkChatAccess($link, $chat_id)) {
                    denyAccess();
                }
            }

            if (!empty($_GET['chat_id']) and !empty($_POST['action']) and !empty($_POST['reaction'])) {
                $chat_id = $_GET['chat_id'];
                $action = $_POST['action'];
                $reaction = $_POST['reaction'];
            } else {
                $chat_id = $_GET['chat_id'];
                $action = '';
                $reaction = '';
            }

            $content = '
            <form method="POST">
                <br>
                chat_id: <input name="chat_id" value="' . $chat_id . '" style="border: none; outline: none;" readonly><br><br>
                <input name="action" value="' . $action . '" placeholder="action"><br><br>
                <textarea name="reaction" placeholder="reaction">' . $reaction . '</textarea><br><br>
                <input type="submit">
            </form>';

            include 'elems/layout.php';
        }

        function addContent($link)
        {
            if (!empty($_GET['chat_id']) and !empty($_POST['action']) and !empty($_POST['reaction'])) {
                $chat_id =$_GET['chat_id'];
                // Проверяем доступ к чату
                if (!checkChatAccess($link, $chat_id)) {
                    denyAccess();
                }
                $action = $_POST['action'];
                $reaction = $_POST['reaction'];
                
                $query = "SELECT COUNT(*) as count FROM rp_actions WHERE chat_id='$chat_id' AND action='$action'";
                $result = pg_query($link, $query) or die('Could not connect: ' . pg_last_error());
                $isContent = pg_fetch_array($result, null, PGSQL_ASSOC)['count'];

                if ($isContent) {
                    $_SESSION['message'] = [
                        'text' => 'Такая команда уже существует!',
                        'status' => 'error'
                    ];
                } else {
                    $query = "INSERT INTO rp_actions (chat_id, action, reaction) VALUES ('$chat_id', $$$action$$, $$$reaction$$)";
                    pg_query($link, $query) or die('Could not connect: ' . pg_last_error());

                    $_SESSION['message'] = [
                        'text' => 'Успешно добавлено',
                        'status' => 'success'
                    ];
                    
                    header("Location: /admin/rp_actions.php?chat_id=$chat_id"); die();

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