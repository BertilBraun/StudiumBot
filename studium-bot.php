<?php

if ($_SERVER['REQUEST_METHOD'] === 'POST') {
	file_put_contents("Schedule.dat", $_POST["schedule"], FILE_APPEND | LOCK_EX);
	if ($_POST['clear'] === 'true') {
		file_put_contents("Schedule.dat", "");
	}
}
if ($_SERVER['REQUEST_METHOD'] === 'GET')  {
    echo file_get_contents("Schedule.dat");
}

?>