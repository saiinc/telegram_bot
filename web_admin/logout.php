<?php
    session_start();
    session_destroy();
    $_SESSION['auth'] = NULL;
    $content = 'Logged out';
    include 'elems/layout.php';