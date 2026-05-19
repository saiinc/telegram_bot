<!DOCTYPE html>
<html>
    <head>
		<meta http-equiv="cache-control" content="no-cache, no-store, must-revalidate">
		<meta name="viewport" content="width=device-width, initial-scale=1.0">
		<link rel="stylesheet" href="style.css?v=1.0">
		<title><?= $title ?></title>
    </head>
    <body>
		<div id="wrapper">
	    	<header>
				<?php 
					if (!empty($_SESSION['auth'])) {
						$username = $_SESSION['username'] ?? 'Гость';
						echo 'Админка Рысёнка';
						echo '<span class="user-info">Пользователь: ' . htmlspecialchars($username) . '</span>';
						echo '<a href="/admin/logout.php">Выход</a>';
					} else { 
						echo '<a href="/admin/login.php">Вход</a>';
					}
				?>
	    	</header>
	    	<main>
				<?php include 'elems/info.php'; ?>
				<?= $content ?>
		    </main>
	    	<footer>
				<br>Copyright 2025 by Anton Sorokin
	    	</footer>
		</div>
        <script>
            document.addEventListener('DOMContentLoaded', function() {
                const timeElements = document.querySelectorAll('.localized-time');
                timeElements.forEach(function(element) {
                    const utcTime = element.getAttribute('data-time');
                    if (utcTime) {
                        const date = new Date(utcTime);
                        element.textContent = date.toLocaleString();
                    }
                });
            });
        </script>
    </body>
</html>