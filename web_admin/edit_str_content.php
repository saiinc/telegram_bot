<?php
    include 'elems/init.php';

    if (!empty($_SESSION['auth'])) {
        function getContent($link)
        {
            $title = 'admin edit str_content';

            if (isset($_GET['id'])){
                $id = $_GET['id'];
                $query = "SELECT * FROM str_content WHERE id='$id'";
                $result = pg_query($link, $query) or die('Could not connect: ' . pg_last_error());
                $str_content = pg_fetch_array($result, null, PGSQL_ASSOC);
                
                if ($str_content) {
                    $chat_id = $str_content['chat_id'];
                    // Проверяем доступ к чату
                    if (!checkChatAccess($link, $chat_id)) {
                        denyAccess();
                    }
                    $content_type = $str_content['content_type'];
                    $is_active = ($str_content['active'] === 't');
                    $is_checked_attribute = $is_active ? 'checked' : '';
                    $value = $str_content['value'];
                
                $content = '
                <form method="POST">
                    <br>
                    chat_id: <input name="chat_id" value="' . $chat_id . '" placeholder="chat_id" style="border: none; outline: none;" readonly><br><br>
                    content_type:<br>
                    <input name="content_type" value="' . $content_type . '" placeholder="chat_id" style="border: none; outline: none;" readonly><br><br>
                    <input type="hidden" name="active" value="0">
                    <input type="checkbox" id="active" name="active" value="1" ' . $is_checked_attribute . '>
                    <label for="active">Active</label><br><br>
                    value:<br>
                    <textarea name="value" placeholder="value" cols="50">' . $value . '</textarea><br><br>
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
            if (!empty($_POST['chat_id']) and !empty($_POST['content_type']) and !empty($_POST['value'])) {
                $chat_id = $_POST['chat_id'];
                // Проверяем доступ к чату
                if (!checkChatAccess($link, $chat_id)) {
                    denyAccess();
                }
                $content_type = $_POST['content_type'];
                $value = $_POST['value'];
                $is_active_from_form = $_POST['active'];
                
                if ($is_active_from_form == 1) {
        	        // Чекбокс был отмечен
        	        echo 'Активен';
    		    } else {
        	        // Чекбокс был снят
        	        echo 'Неактивен';
    		    }
                
                //$query = "SELECT COUNT(*) as count FROM helper WHERE chat_id='$chat_id' AND command='$command'";
                //$result = pg_query($link, $query) or die('Could not connect: ' . pg_last_error());
                //$isContent = pg_fetch_array($result, null, PGSQL_ASSOC)['count'];

                if (isset($_GET['id'])) {
                    $id = $_GET['id'];
                    $query = "UPDATE str_content SET chat_id = '$chat_id', created_at = CURRENT_TIMESTAMP, content_type = $$$content_type$$, value = $$$value$$, active = '$is_active_from_form' WHERE id = '$id'";
                    pg_query($link, $query) or die('Could not connect: ' . pg_last_error());
                    $_SESSION['message'] = [
                        'text' => 'Успешно отредактировано',
                        'status' => 'success'
                    ];
                    header("Location: /admin/str_content.php?chat_id=$chat_id&content_type=$content_type"); die();
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