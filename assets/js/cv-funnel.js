/**
 * CV Lead Capture Funnel
 * Intercepts the Download CV button, shows a lead capture modal,
 * submits to /forms/cv-lead.php, then triggers the download.
 *
 * Analytics events (fires via gtag if GA is loaded):
 *   cv_click       — user clicks the Download CV button
 *   cv_form_open   — modal opens
 *   cv_form_submit — form submitted successfully
 *   cv_download    — CV file triggered for download
 */
(function () {
  'use strict';

  const CV_URL  = '/assets/docs/jonathan-mupini-resume.pdf';
  const API_URL = '/forms/cv-lead.php';

  // Read ?ref= tracking param from the page URL
  const ref = new URLSearchParams(window.location.search).get('ref') || '';

  // ── Analytics helper ──────────────────────────────────────────────────────────
  function track(eventName, params) {
    var p = Object.assign({}, params || {});
    if (ref) p.cv_ref = ref;
    try {
      if (typeof gtag === 'function') gtag('event', eventName, p);
    } catch (_) { /* GA not loaded — no-op */ }
  }

  // ── Modal CSS (injected once, non-blocking) ───────────────────────────────────
  function injectStyles() {
    if (document.getElementById('cv-funnel-styles')) return;
    var s = document.createElement('style');
    s.id  = 'cv-funnel-styles';
    s.textContent = [
      /* Overlay */
      '#cv-modal-overlay{display:none;position:fixed;inset:0;z-index:10000;',
        'background:rgba(0,0,0,.55);backdrop-filter:blur(4px);',
        '-webkit-backdrop-filter:blur(4px);',
        'align-items:center;justify-content:center;padding:1rem}',
      '#cv-modal-overlay.cv-modal-open{display:flex}',

      /* Card */
      '#cv-modal{position:relative;background:#fff;border-radius:20px;',
        'padding:2rem;width:100%;max-width:460px;',
        'box-shadow:0 20px 60px rgba(0,0,0,.18);',
        'max-height:90vh;overflow-y:auto}',

      /* Close button */
      '#cv-modal-close{position:absolute;top:.85rem;right:1rem;',
        'background:none;border:none;font-size:1.5rem;line-height:1;',
        'cursor:pointer;color:#6e6e73;padding:.25rem .4rem;border-radius:6px}',
      '#cv-modal-close:hover{background:#f5f5f7;color:#1d1d1f}',

      /* Header row */
      '.cv-modal-header{display:flex;align-items:flex-start;gap:.9rem;margin-bottom:1.5rem}',
      '.cv-modal-header svg{flex-shrink:0;margin-top:.15rem}',
      '.cv-modal-header h2{font-size:1.2rem;font-weight:700;margin:0 0 .2rem;',
        'color:#1d1d1f;letter-spacing:-.02em}',
      '.cv-modal-header p{font-size:.85rem;color:#6e6e73;margin:0}',

      /* Fields */
      '.cv-field{margin-bottom:1rem}',
      '.cv-field label{display:block;font-size:.82rem;font-weight:600;',
        'color:#1d1d1f;margin-bottom:.35rem}',
      '.cv-field label span[aria-hidden]{color:#e53e3e}',
      '.cv-optional{font-weight:400;color:#6e6e73}',
      '.cv-field input,.cv-field select{width:100%;padding:.6rem .85rem;',
        'border:1.5px solid #d1d1d6;border-radius:10px;font-size:.9rem;',
        'color:#1d1d1f;background:#fff;outline:none;transition:border-color .2s}',
      '.cv-field input:focus,.cv-field select:focus{border-color:#0071e3;',
        'box-shadow:0 0 0 3px rgba(0,113,227,.12)}',
      '.cv-field input.cv-invalid,.cv-field select.cv-invalid{border-color:#e53e3e}',
      '.cv-field-error{display:none;font-size:.77rem;color:#e53e3e;',
        'margin-top:.3rem}',

      /* Global form error */
      '.cv-global-error{font-size:.83rem;color:#e53e3e;min-height:1.2em;',
        'margin-bottom:.5rem;text-align:center}',

      /* Submit button */
      '#cv-submit-btn{width:100%;padding:.75rem;border:none;border-radius:980px;',
        'background:#0071e3;color:#fff;font-size:.95rem;font-weight:600;',
        'cursor:pointer;display:flex;align-items:center;justify-content:center;',
        'gap:.5rem;transition:background .2s,transform .1s;margin-top:.25rem}',
      '#cv-submit-btn:hover:not(:disabled){background:#0062c4}',
      '#cv-submit-btn:active:not(:disabled){transform:scale(.98)}',
      '#cv-submit-btn:disabled{opacity:.6;cursor:not-allowed}',

      /* Spinner */
      '.cv-spin{animation:cv-rotate 1s linear infinite}',
      '@keyframes cv-rotate{from{transform:rotate(0deg)}to{transform:rotate(360deg)}}',

      /* Privacy note */
      '.cv-privacy{font-size:.75rem;color:#6e6e73;text-align:center;margin:.75rem 0 0}',

      /* Confirmation */
      '#cv-step-confirm{text-align:center;padding:.5rem 0}',
      '.cv-confirm-icon{margin-bottom:1rem}',
      '#cv-step-confirm h2{font-size:1.25rem;font-weight:700;color:#1d1d1f;',
        'margin:0 0 .5rem;letter-spacing:-.02em}',
      '#cv-step-confirm p{font-size:.9rem;color:#6e6e73;margin:0 0 1rem}',
      '.cv-manual-dl{display:inline-block;font-size:.82rem;color:#0071e3;',
        'text-decoration:underline;margin-bottom:1.5rem}',

      /* CTA grid */
      '.cv-cta-grid{display:flex;flex-direction:column;gap:.6rem}',
      '.cv-cta-btn{display:flex;align-items:center;justify-content:center;',
        'gap:.5rem;padding:.65rem 1rem;border-radius:980px;font-size:.88rem;',
        'font-weight:600;text-decoration:none;transition:all .2s}',
      '.cv-cta-primary{background:#0071e3;color:#fff}',
      '.cv-cta-primary:hover{background:#0062c4;color:#fff;text-decoration:none}',
      '.cv-cta-secondary{background:#f5f5f7;color:#1d1d1f;',
        'border:1.5px solid #e8e8ed}',
      '.cv-cta-secondary:hover{border-color:#0071e3;color:#0071e3;',
        'text-decoration:none}',

      /* Mobile */
      '@media(max-width:500px){#cv-modal{padding:1.5rem 1.25rem;border-radius:16px}}',
    ].join('');
    document.head.appendChild(s);
  }

  // ── Build modal DOM (once) ────────────────────────────────────────────────────
  function buildModal() {
    var el = document.createElement('div');
    el.id = 'cv-modal-overlay';
    el.setAttribute('role', 'dialog');
    el.setAttribute('aria-modal', 'true');
    el.setAttribute('aria-labelledby', 'cv-modal-title');
    el.setAttribute('aria-hidden', 'true');
    el.innerHTML =
      '<div id="cv-modal" role="document">' +
        '<button id="cv-modal-close" aria-label="Close">&times;</button>' +

        // ── Step 1: Form ──
        '<div id="cv-step-form">' +
          '<div class="cv-modal-header">' +
            '<svg width="36" height="36" viewBox="0 0 24 24" fill="none" stroke="#0071e3" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">' +
              '<path d="M13 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9z"/>' +
              '<polyline points="13 2 13 9 20 9"/>' +
              '<line x1="8" y1="13" x2="16" y2="13"/>' +
              '<line x1="8" y1="17" x2="12" y2="17"/>' +
            '</svg>' +
            '<div>' +
              '<h2 id="cv-modal-title">Get my CV</h2>' +
              '<p>Quick form, then it downloads instantly.</p>' +
            '</div>' +
          '</div>' +

          '<form id="cv-lead-form" novalidate autocomplete="on">' +
            /* Honeypot — visually hidden, real users never fill it */
            '<div style="position:absolute;left:-9999px;top:-9999px" aria-hidden="true">' +
              '<label>Leave blank<input type="text" name="website" id="cv-hp" tabindex="-1" autocomplete="off"></label>' +
            '</div>' +

            '<div class="cv-field">' +
              '<label for="cv-name">Full Name <span aria-hidden="true">*</span></label>' +
              '<input type="text" id="cv-name" name="name" placeholder="Jonathan Mupini" required autocomplete="name" maxlength="120">' +
              '<span class="cv-field-error" id="cv-name-err" role="alert"></span>' +
            '</div>' +

            '<div class="cv-field">' +
              '<label for="cv-email">Email Address <span aria-hidden="true">*</span></label>' +
              '<input type="email" id="cv-email" name="email" placeholder="you@company.com" required autocomplete="email" maxlength="254">' +
              '<span class="cv-field-error" id="cv-email-err" role="alert"></span>' +
            '</div>' +

            '<div class="cv-field">' +
              '<label for="cv-company">Company / Organisation <span class="cv-optional">(optional)</span></label>' +
              '<input type="text" id="cv-company" name="company" placeholder="Acme Corp" autocomplete="organization" maxlength="120">' +
            '</div>' +

            '<div class="cv-field">' +
              '<label for="cv-intent">What brings you here? <span class="cv-optional">(optional)</span></label>' +
              '<select id="cv-intent" name="intent">' +
                '<option value="">Select\u2026</option>' +
                '<option value="hiring">Hiring / Recruiting</option>' +
                '<option value="freelance">Freelance project</option>' +
                '<option value="browsing">Just browsing</option>' +
              '</select>' +
            '</div>' +

            '<div id="cv-form-error" class="cv-global-error" role="alert" aria-live="polite"></div>' +

            '<button type="submit" id="cv-submit-btn">' +
              '<span id="cv-submit-label">Get the CV</span>' +
              '<span id="cv-submit-spinner" hidden>' +
                '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true" class="cv-spin">' +
                  '<circle cx="12" cy="12" r="10" stroke-opacity=".25"/>' +
                  '<path d="M12 2a10 10 0 0 1 10 10"/>' +
                '</svg>' +
                ' Sending\u2026' +
              '</span>' +
            '</button>' +

            '<p class="cv-privacy">No spam. Your details are only used to follow up if you reach out.</p>' +
          '</form>' +
        '</div>' +

        // ── Step 2: Confirmation ──
        '<div id="cv-step-confirm" hidden>' +
          '<div class="cv-confirm-icon">' +
            '<svg width="52" height="52" viewBox="0 0 24 24" fill="none" stroke="#34c759" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">' +
              '<circle cx="12" cy="12" r="10"/><polyline points="9 12 11.5 14.5 15.5 10"/>' +
            '</svg>' +
          '</div>' +
          '<h2 id="cv-confirm-title" tabindex="-1">Your CV is downloading</h2>' +
          '<p>Thanks! Check your downloads folder. A copy is also heading to your inbox.</p>' +
          '<a id="cv-manual-link" href="' + CV_URL + '" download="Jonathan_Mupini_CV.pdf" class="cv-manual-dl">' +
            'Didn\u2019t start? Click to download manually' +
          '</a>' +
          '<div class="cv-cta-grid">' +
            '<a href="/#portfolio" class="cv-cta-btn cv-cta-primary">' +
              '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><rect x="2" y="3" width="20" height="14" rx="2"/><line x1="8" y1="21" x2="16" y2="21"/><line x1="12" y1="17" x2="12" y2="21"/></svg>' +
              ' See my projects' +
            '</a>' +
            '<a href="mailto:ejmupini@gmail.com" class="cv-cta-btn cv-cta-secondary">' +
              '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z"/><polyline points="22,6 12,13 2,6"/></svg>' +
              ' Send me a message' +
            '</a>' +
            '<a href="https://zw.linkedin.com/in/jonathanebenmupini" target="_blank" rel="noopener noreferrer" class="cv-cta-btn cv-cta-secondary">' +
              '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M16 8a6 6 0 0 1 6 6v7h-4v-7a2 2 0 0 0-4 0v7h-4v-7a6 6 0 0 1 6-6z"/><rect x="2" y="9" width="4" height="12"/><circle cx="4" cy="4" r="2"/></svg>' +
              ' Connect on LinkedIn' +
            '</a>' +
          '</div>' +
        '</div>' +

      '</div>'; // #cv-modal

    document.body.appendChild(el);
    return el;
  }

  // ── Field validation helpers ──────────────────────────────────────────────────
  function setFieldError(inputId, errId, msg) {
    var input = document.getElementById(inputId);
    var err   = document.getElementById(errId);
    if (input) input.classList.add('cv-invalid');
    if (err)   { err.textContent = msg; err.style.display = 'block'; }
  }

  function clearFieldError(inputId, errId) {
    var input = document.getElementById(inputId);
    var err   = document.getElementById(errId);
    if (input) input.classList.remove('cv-invalid');
    if (err)   { err.textContent = ''; err.style.display = 'none'; }
  }

  function validateForm() {
    var ok    = true;
    var name  = (document.getElementById('cv-name')  || {}).value || '';
    var email = (document.getElementById('cv-email') || {}).value || '';

    clearFieldError('cv-name',  'cv-name-err');
    clearFieldError('cv-email', 'cv-email-err');

    if (!name.trim()) {
      setFieldError('cv-name', 'cv-name-err', 'Please enter your full name.');
      ok = false;
    }
    if (!email.trim()) {
      setFieldError('cv-email', 'cv-email-err', 'Please enter your email address.');
      ok = false;
    } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/.test(email.trim())) {
      setFieldError('cv-email', 'cv-email-err', 'Please enter a valid email address.');
      ok = false;
    }
    return ok;
  }

  // ── Modal open / close ────────────────────────────────────────────────────────
  var overlay = null;

  function openModal() {
    if (!overlay) {
      injectStyles();
      overlay = buildModal();
    }

    // Reset to form step
    document.getElementById('cv-step-form').hidden    = false;
    document.getElementById('cv-step-confirm').hidden = true;
    document.getElementById('cv-lead-form').reset();
    document.getElementById('cv-form-error').textContent = '';
    clearFieldError('cv-name',  'cv-name-err');
    clearFieldError('cv-email', 'cv-email-err');

    overlay.classList.add('cv-modal-open');
    overlay.setAttribute('aria-hidden', 'false');
    document.body.style.overflow = 'hidden';

    setTimeout(function () {
      var f = document.getElementById('cv-name');
      if (f) f.focus();
    }, 80);

    document.getElementById('cv-modal-close').onclick = closeModal;
    overlay.addEventListener('click', onOverlayClick);
    document.addEventListener('keydown', onEscape);
    document.getElementById('cv-lead-form').addEventListener('submit', onFormSubmit);

    track('cv_form_open');
  }

  function closeModal() {
    if (!overlay) return;
    overlay.classList.remove('cv-modal-open');
    overlay.setAttribute('aria-hidden', 'true');
    document.body.style.overflow = '';
    overlay.removeEventListener('click', onOverlayClick);
    document.removeEventListener('keydown', onEscape);
    // Remove submit listener to avoid double-binding on reopen
    var form = document.getElementById('cv-lead-form');
    if (form) form.removeEventListener('submit', onFormSubmit);
  }

  function onOverlayClick(e) { if (e.target === overlay) closeModal(); }
  function onEscape(e)       { if (e.key === 'Escape')    closeModal(); }

  // ── Form submission ───────────────────────────────────────────────────────────
  function onFormSubmit(e) {
    e.preventDefault();
    if (!validateForm()) return;

    // Honeypot — abort silently if filled
    var hp = document.getElementById('cv-hp');
    if (hp && hp.value) return;

    var submitBtn   = document.getElementById('cv-submit-btn');
    var submitLabel = document.getElementById('cv-submit-label');
    var spinner     = document.getElementById('cv-submit-spinner');
    var globalErr   = document.getElementById('cv-form-error');

    submitBtn.disabled    = true;
    submitLabel.hidden    = true;
    spinner.hidden        = false;
    globalErr.textContent = '';

    var formData = new FormData();
    formData.append('name',    document.getElementById('cv-name').value.trim());
    formData.append('email',   document.getElementById('cv-email').value.trim());
    formData.append('company', document.getElementById('cv-company').value.trim());
    formData.append('intent',  document.getElementById('cv-intent').value);
    formData.append('ref',     ref);
    formData.append('website', hp ? hp.value : ''); // honeypot

    var intent = document.getElementById('cv-intent').value || 'not_set';
    track('cv_form_submit', { intent: intent });

    fetch(API_URL, { method: 'POST', body: formData })
      .then(function (res) { return res.json(); })
      .then(function (data) {
        if (data.ok) {
          showConfirmation();
          triggerDownload(CV_URL);
          track('cv_download', { intent: intent });
        } else {
          globalErr.textContent = data.message || 'Something went wrong. Please try again.';
          submitBtn.disabled = false;
          submitLabel.hidden = false;
          spinner.hidden     = true;
        }
      })
      .catch(function () {
        // Network failure — allow download anyway, don't penalise the user
        showConfirmation();
        triggerDownload(CV_URL);
        track('cv_download', { intent: intent, note: 'network_fallback' });
      });
  }

  function showConfirmation() {
    document.getElementById('cv-step-form').hidden    = true;
    document.getElementById('cv-step-confirm').hidden = false;
    var title = document.getElementById('cv-confirm-title');
    if (title) title.focus();
  }

  function triggerDownload(url) {
    var a = document.createElement('a');
    a.href     = url;
    a.download = 'Jonathan_Mupini_CV.pdf';
    a.style.cssText = 'position:absolute;left:-9999px';
    document.body.appendChild(a);
    a.click();
    setTimeout(function () { document.body.removeChild(a); }, 2000);
  }

  // ── Init ──────────────────────────────────────────────────────────────────────
  function init() {
    var btn = document.getElementById('download-cv');
    if (!btn) return;

    // Neutralise any direct link/download attributes
    btn.removeAttribute('href');
    btn.removeAttribute('download');
    if (btn.tagName === 'A') {
      btn.setAttribute('role', 'button');
      btn.setAttribute('tabindex', '0');
    }

    btn.addEventListener('click', function (e) {
      e.preventDefault();
      track('cv_click');
      openModal();
    });

    // Keyboard activation for <a> used as button
    btn.addEventListener('keydown', function (e) {
      if (e.key === 'Enter' || e.key === ' ') {
        e.preventDefault();
        btn.click();
      }
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

})();
