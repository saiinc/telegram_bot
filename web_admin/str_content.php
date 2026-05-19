<?php
    
    include 'elems/init.php';
    
    if (!empty($_SESSION['auth'])) {
        function showStrContent($link)
        {
            $title = 'admin str_content page';
            if (isset($_GET['chat_id'])){
                $chat_id = $_GET['chat_id'];
                // Проверяем доступ к чату
                if (!checkChatAccess($link, $chat_id)) {
                    denyAccess();
                }
                $content_type = $_GET['content_type'];
                
                // Загрузка всех данных без сортировки
                $query = "SELECT * FROM str_content WHERE chat_id='$chat_id' AND content_type='$content_type' ORDER BY value";
                $result = pg_query($link, $query) or die('Could not connect: ' . pg_last_error());
                for ($data = []; $row = pg_fetch_array($result, null, PGSQL_ASSOC); $data[] = $row );
                if ($data) {
                    $content = <<<HTML
                        <br><a href="/admin/">К списку чатов</a><br><br>
                        <a href="/admin/add_str_content.php?chat_id={$chat_id}&content_type={$content_type}">Добавить новую запись</a><br><br>
                        chat_id {$chat_id}
                        <table>
                        <thead>
                        <tr>
                            <th onclick="sortTable(0, 'string')"><span class="sortable-header">{$content_type}</span></th>
                            <th onclick="sortTable(1, 'boolean')"><span class="sortable-header">active</span></th>
                            <th onclick="sortTable(2, 'date')"><span class="sortable-header">modified</span></th>
                            <th>edit</th>
                            <th>delete</th>
                        </tr>
                        </thead>
                        <tbody>
                        HTML;
                    foreach ($data as $str_content) {
                    $is_active = ($str_content['active'] === 't');
                    $is_checked_attribute = $is_active ? '✅' : '❌';
                    $content .= "<tr>
                                    <td>{$str_content['value']}</td>
                                    <td>{$is_checked_attribute}</td>
                                    <td class=\"localized-time\" data-time=\"" . htmlspecialchars($str_content['created_at']) . "\"></td>
                                    <td><a href=\"/admin/edit_str_content.php?id={$str_content['id']}\">edit</a></td>
                                    <td><a href=\"?delete={$str_content['id']}&chat_id={$chat_id}&content_type={$content_type}\">delete</a></td>
                                </tr>";
                    }
                    $content .= '</tbody></table>';
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
                $content_type = $_GET['content_type'];
                $query = "DELETE FROM str_content WHERE id=$id";
                pg_query($link, $query) or die('Could not connect: ' . pg_last_error());
                $_SESSION['message'] = [
                    'text' => 'Запись удалена',
                    'status' => 'success'
                ];
                header("Location: /admin/str_content.php?chat_id=$chat_id&content_type=$content_type"); die();
            }  
        } 
        deletePage($link);

        showStrContent($link);
    } else {
        header('Location: /admin/login.php'); die();
    }
?>

<script>
     let currentSortColumn = 0;
     let currentSortDirection = 'asc';
    
     // Инициализация после загрузки страницы
     document.addEventListener('DOMContentLoaded', function() {
         const headers = document.querySelectorAll('th');
         if (headers.length > 0) {
             // Добавляем индикатор сортировки для первого заголовка
             const firstHeader = headers[0];
             const originalText = firstHeader.textContent;
             firstHeader.innerHTML = '<span class="sortable-header">' + originalText + ' ↑</span>';
        }
    });
   
    function sortTable(columnIndex, dataType) {
        const table = document.querySelector('table');
        const tbody = table.querySelector('tbody');
        const rows = Array.from(tbody.querySelectorAll('tr'));
        const headers = table.querySelectorAll('th');
   
        // Проверяем, кликнули ли по той же колонке
        if (currentSortColumn === columnIndex) {
            currentSortDirection = currentSortDirection === 'asc' ? 'desc' : 'asc';
        } else {
            currentSortDirection = 'asc';
        }
   
        currentSortColumn = columnIndex;
   
        // Обновляем заголовки
        headers.forEach((header, index) => {
            const originalText = header.textContent.replace(/[ ↑↓]*$/, '');
            if (index === currentSortColumn) {
                header.innerHTML = '<span class="sortable-header">' + originalText + (currentSortDirection === 'asc' ? ' ↑' : ' ↓') + '</span>';
            } else {
                header.innerHTML = '<span class="sortable-header">' + originalText + '</span>';
            }
        });
   
        rows.sort((a, b) => {
            const aValue = a.cells[columnIndex].textContent.trim();
            const bValue = b.cells[columnIndex].textContent.trim();
   
            let result = 0;
            if (dataType === 'date') {
                const aDate = new Date(a.cells[2].getAttribute('data-time'));
                const bDate = new Date(b.cells[2].getAttribute('data-time'));
                result = aDate - bDate;
            } else if (dataType === 'boolean') {
                result = aValue.localeCompare(bValue);
            } else {
                result = aValue.localeCompare(bValue, undefined, {numeric: true, sensitivity: 'base'});
            }
   
            return currentSortDirection === 'asc' ? result : -result;
        });
   
        rows.forEach(row => tbody.appendChild(row));
    }
</script>
