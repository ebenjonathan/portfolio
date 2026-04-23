<?php
/**
 * Contact form handler for Jonathan Mupini's portfolio.
 * Sends submitted messages to the configured email address.
 */

// ── Configuration ─────────────────────────────────────────
$receiving_email = 'ejmupini@gmail.com';
$site_name       = 'Jonathan Mupini Portfolio';
// ──────────────────────────────────────────────────────────

// Only accept POST requests
if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
    http_response_code(405);
    exit('Method Not Allowed');
}

// Sanitize inputs
function clean(string $value): string {
    return htmlspecialchars(strip_tags(trim($value)), ENT_QUOTES, 'UTF-8');
}

$name    = clean($_POST['name']    ?? '');
$email   = clean($_POST['email']   ?? '');
$subject = clean($_POST['subject'] ?? '');
$message = clean($_POST['message'] ?? '');

// Validate required fields
if (empty($name) || empty($email) || empty($subject) || empty($message)) {
    http_response_code(400);
    exit('Please fill in all fields.');
}

// Validate email address
if (!filter_var($_POST['email'], FILTER_VALIDATE_EMAIL)) {
    http_response_code(400);
    exit('Invalid email address.');
}

// Build email
$to      = $receiving_email;
$headers = implode("\r\n", [
    'MIME-Version: 1.0',
    'Content-Type: text/plain; charset=UTF-8',
    "From: {$site_name} <{$receiving_email}>",
    "Reply-To: {$name} <{$email}>",
    'X-Mailer: PHP/' . phpversion(),
]);

$body = "You have received a new message via your portfolio contact form.\n\n"
      . "Name:    {$name}\n"
      . "Email:   {$email}\n"
      . "Subject: {$subject}\n\n"
      . "Message:\n{$message}\n";

// Send and respond (validate.js expects plain "OK" on success)
if (mail($to, "Portfolio Contact: {$subject}", $body, $headers)) {
    http_response_code(200);
    echo 'OK';
} else {
    error_log('contact.php: failed to send portfolio contact email from ' . $email);
    http_response_code(500);
    echo 'Could not send the message. Please try again or email directly at ' . $receiving_email;
}
