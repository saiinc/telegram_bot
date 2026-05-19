<?php
    include 'elems/init.php';

    if (!empty($_SESSION['auth'])) {
        function getContent($link)
        {
            $title = 'admin add new content';

            if (isset($_GET['id'])){
                $id = $_GET['id'];
                $query = "SELECT * FROM rp_actions WHERE id='$id'";
                $result = pg_query($link, $query) or die('Could not connect: ' . pg_last_error());
                $rp_actions = pg_fetch_array($result, null, PGSQL_ASSOC);
                
                if ($rp_actions) {
                    $chat_id = $rp_actions['chat_id'];
                    // Проверяем доступ к чату
                    if (!checkChatAccess($link, $chat_id)) {
                        denyAccess();
                    }
                    $action = $rp_actions['action'];
                    $reaction = $rp_actions['reaction'];
                
                $content = '
                <form method="POST">
                    <br>
                    chat_id: <input name="chat_id" value="' . $chat_id . '" placeholder="chat_id" style="border: none; outline: none;" readonly><br><br>
                    action:<br>
                    <input name="action" value="' . $action . '" placeholder="action"><br><br>
                    reaction:<br>
                    <textarea name="reaction" placeholder="reaction" cols="50">' . $reaction . '</textarea><br><br>
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
            if (!empty($_POST['chat_id']) and !empty($_POST['action']) and !empty($_POST['reaction'])) {
                $chat_id = $_POST['chat_id'];
                // Проверяем доступ к чату
                if (!checkChatAccess($link, $chat_id)) {
                    denyAccess();
                }
                $action = $_POST['action'];
                $reaction = $_POST['reaction'];
                
                //$query = "SELECT COUNT(*) as count FROM helper WHERE chat_id='$chat_id' AND command='$command'";
                //$result = pg_query($link, $query) or die('Could not connect: ' . pg_last_error());
                //$isContent = pg_fetch_array($result, null, PGSQL_ASSOC)['count'];

                if (isset($_GET['id'])) {
                    $id = $_GET['id'];
                    $query = "UPDATE rp_actions SET chat_id = '$chat_id', action = $$$action$$, reaction = $$$reaction$$ WHERE id = '$id'";
                    pg_query($link, $query) or die('Could not connect: ' . pg_last_error());
                    $_SESSION['message'] = [
                        'text' => 'Успешно отредактировано',
                        'status' => 'success'
                    ];
                    header("Location: /admin/rp_actions.php?chat_id=$chat_id"); die();
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