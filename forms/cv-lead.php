<?php
/**
 * CV Lead Capture Endpoint
 * Accepts POST, validates, rate-limits, stores lead, sends emails.
 */

// ── Configuration ──────────────────────────────────────────────────────────────
const OWNER_EMAIL   = 'ejmupini@gmail.com';
const PORTFOLIO_URL = 'https://www.mupinilabs.com';
const CV_URL        = 'https://www.mupinilabs.com/assets/docs/jonathan-mupini-resume.pdf';
const LEADS_FILE    = __DIR__ . '/../data/cv-leads.ndjson';
const RATE_LIMIT    = 3;          // max submissions per window
const RATE_WINDOW   = 3600;       // window in seconds (1 hour)
// ───────────────────────────────────────────────────────────────────────────────

header('Content-Type: application/json; charset=UTF-8');
header('X-Content-Type-Options: nosniff');
header('X-Frame-Options: DENY');

// Only accept POST
if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
    http_response_code(405);
    exit(json_encode(['ok' => false, 'message' => 'Method not allowed.']));
}

// ── Honeypot ────────────────────────────────────────────────────────────────────
// Field named "website" must be empty — bots usually fill all fields
if (!empty($_POST['website'])) {
    // Silently succeed to not reveal the check to bots
    http_response_code(200);
    exit(json_encode(['ok' => true]));
}

// ── Sanitize inputs ─────────────────────────────────────────────────────────────
function clean(string $value, int $maxLen = 255): string {
    return htmlspecialchars(strip_tags(trim(substr($value, 0, $maxLen))), ENT_QUOTES, 'UTF-8');
}

$name    = clean($_POST['name']    ?? '', 120);
$email   = trim($_POST['email']    ?? '');
$company = clean($_POST['company'] ?? '', 120);
$intent  = clean($_POST['intent']  ?? '', 20);
$ref     = clean($_POST['ref']     ?? '', 100);

// ── Validate ─────────────────────────────────────────────────────────────────────
if (empty($name)) {
    http_response_code(400);
    exit(json_encode(['ok' => false, 'message' => 'Full name is required.']));
}

if (empty($email) || !filter_var($email, FILTER_VALIDATE_EMAIL)) {
    http_response_code(400);
    exit(json_encode(['ok' => false, 'message' => 'A valid email address is required.']));
}

// Sanitize email only after format validation
$email = filter_var($email, FILTER_SANITIZE_EMAIL);

$allowed_intents = ['hiring', 'freelance', 'browsing', ''];
if (!in_array($intent, $allowed_intents, true)) {
    $intent = '';
}

// ── Rate limiting (per IP, stored in system temp dir) ────────────────────────────
$ip      = $_SERVER['REMOTE_ADDR'] ?? '0.0.0.0';
$ipHash  = hash('sha256', $ip);  // never store raw IPs
$rlFile  = sys_get_temp_dir() . DIRECTORY_SEPARATOR . 'cvlead_' . $ipHash . '.json';
$now     = time();

if (file_exists($rlFile)) {
    $rl = json_decode(file_get_contents($rlFile), true);
    if (!is_array($rl)) {
        $rl = ['count' => 0, 'window_start' => $now];
    }
    if ($now - $rl['window_start'] < RATE_WINDOW) {
        if ($rl['count'] >= RATE_LIMIT) {
            http_response_code(429);
            exit(json_encode(['ok' => false, 'message' => 'Too many requests. Please try again in an hour.']));
        }
        $rl['count']++;
    } else {
        $rl = ['count' => 1, 'window_start' => $now];
    }
} else {
    $rl = ['count' => 1, 'window_start' => $now];
}

file_put_contents($rlFile, json_encode($rl), LOCK_EX);

// ── Store lead ────────────────────────────────────────────────────────────────────
$lead = [
    'timestamp'  => date('c'),
    'name'       => $name,
    'email'      => $email,
    'company'    => $company,
    'intent'     => $intent,
    'ref'        => $ref,
    'ip_hash'    => substr($ipHash, 0, 16),  // truncated hash, not raw IP
    'user_agent' => substr($_SERVER['HTTP_USER_AGENT'] ?? '', 0, 200),
];

$leadsDir = dirname(LEADS_FILE);
if (!is_dir($leadsDir)) {
    mkdir($leadsDir, 0750, true);
}

file_put_contents(LEADS_FILE, json_encode($lead) . "\n", FILE_APPEND | LOCK_EX);

// ── Notify owner ──────────────────────────────────────────────────────────────────
$notifySubject = "New CV Lead: {$name}" . ($company ? " ({$company})" : '');
$notifyBody    = "New CV download lead from your portfolio.\n\n"
    . "Name:      {$name}\n"
    . "Email:     {$email}\n"
    . "Company:   " . ($company ?: '(not provided)') . "\n"
    . "Intent:    " . ($intent  ?: '(not specified)') . "\n"
    . "Ref:       " . ($ref     ?: '(direct)') . "\n"
    . "Time:      {$lead['timestamp']}\n";

$notifyHeaders = implode("\r\n", [
    'MIME-Version: 1.0',
    'Content-Type: text/plain; charset=UTF-8',
    'From: Portfolio CV Funnel <' . OWNER_EMAIL . '>',
    'X-Mailer: PHP/' . phpversion(),
]);

$ownerMailSent = mail(OWNER_EMAIL, $notifySubject, $notifyBody, $notifyHeaders);
if (!$ownerMailSent) {
    error_log('cv-lead.php: failed to send owner notification email for lead ' . $email);
}

// ── Send thank-you to lead ────────────────────────────────────────────────────────
$thanksSubject = "Your download is ready — Jonathan Mupini's CV";
$thanksBody    = "Hi {$name},\n\n"
    . "Thanks for downloading my CV. Here's a direct link if the download didn't start automatically:\n\n"
    . CV_URL . "\n\n"
    . "You can browse my full portfolio and case studies at:\n"
    . PORTFOLIO_URL . "\n\n"
    . "If you have a project or role in mind, I'd love to hear from you:\n"
    . "  Email:    " . OWNER_EMAIL . "\n"
    . "  LinkedIn: https://zw.linkedin.com/in/jonathanebenmupini\n\n"
    . "Looking forward to connecting.\n\n"
    . "Best,\n"
    . "Jonathan Mupini\n"
    . "Software Developer · IT Consultant\n"
    . PORTFOLIO_URL . "\n";

$thanksHeaders = implode("\r\n", [
    'MIME-Version: 1.0',
    'Content-Type: text/plain; charset=UTF-8',
    'From: Jonathan Mupini <' . OWNER_EMAIL . '>',
    'Reply-To: Jonathan Mupini <' . OWNER_EMAIL . '>',
    'X-Mailer: PHP/' . phpversion(),
]);

$leadMailSent = mail($email, $thanksSubject, $thanksBody, $thanksHeaders);
if (!$leadMailSent) {
    error_log('cv-lead.php: failed to send thank-you email to lead ' . $email);
}

// ── Respond ───────────────────────────────────────────────────────────────────────
http_response_code(200);
echo json_encode([
    'ok' => true,
    'cv_url' => CV_URL,
    'email_status' => [
        'owner_notification_sent' => $ownerMailSent,
        'lead_thankyou_sent' => $leadMailSent,
    ],
]);
