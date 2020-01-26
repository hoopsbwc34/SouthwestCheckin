
<HTML>
<Body>
<?php
include 'db_connection.php';

if($_SERVER["REQUEST_METHOD"] == "POST") {
    $conf=test_input($_POST['element_1']);
    $first=test_input($_POST['element_2']);
    $last=test_input($_POST['element_3']);
}

function test_input($data) {
    $data = trim($data);
    $data = stripslashes($data);
    $data = htmlspecialchars($data);
    return $data;
}

if((!empty($_POST['element_1'])) AND (!empty($_POST['element_2'])) AND (!empty($_POST['element_3']))){
    $sql = "SELECT COUNT(*) as total FROM flightinfo WHERE conf='$conf'AND first='$first' AND last='$last'";
    $result = mysqli_query($conn,$sql);
    $data = mysqli_fetch_assoc($result);
    if($data['total']>=1){
        echo "Duplicate Entry!";
        exit;
    }
    else{
        $sql = "INSERT into flightinfo (conf, first, last) VALUES ('$conf', '$first', '$last')";
    }
} else {   
    echo "ERROR: Confirmation number, first and last name are required ";
    exit;
}

if(!(strlen($conf)==6)){
    echo "Confirmation number must be six digits";
    exit;
}

if(mysqli_query($conn, $sql)){
    echo "Submitted!";
} else{
    echo "ERROR: Failed to execute $sql. " . mysqli_error($conn);
}

?>
</Body>
</HTML>
