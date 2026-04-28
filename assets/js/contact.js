(function () {
  'use strict';

  const form = document.querySelector('.php-email-form');
  if (!form) return;

  async function submitContact(formData) {
    return fetch('/api/contact', {
      method: 'POST',
      body: formData
    });
  }

  async function readErrorMessage(response) {
    const contentType = response.headers.get('content-type') || '';

    try {
      if (contentType.includes('application/json')) {
        const data = await response.json();
        if (data && typeof data.message === 'string' && data.message.trim()) {
          return data.message.trim();
        }
      } else {
        const text = (await response.text()).trim();
        if (text) return text;
      }
    } catch (_err) {
      // Ignore parse errors and fall back to generic message.
    }

    return 'Submission failed. Please try again.';
  }

  form.addEventListener('submit', async function (e) {
    e.preventDefault();

    const loading  = form.querySelector('.loading');
    const errorMsg = form.querySelector('.error-message');
    const sentMsg  = form.querySelector('.sent-message');

    loading.classList.add('d-block');
    errorMsg.classList.remove('d-block');
    sentMsg.classList.remove('d-block');

    try {
      const res = await submitContact(new FormData(form));

      loading.classList.remove('d-block');

      if (res.ok === true) {
        sentMsg.classList.add('d-block');
        form.reset();
      } else {
        throw new Error(await readErrorMessage(res));
      }
    } catch (err) {
      loading.classList.remove('d-block');
      errorMsg.textContent = err && err.message ? err.message : 'Submission failed. Please try again.';
      errorMsg.classList.add('d-block');
    }
  });
})();
