(function () {
  'use strict';

  const form = document.querySelector('.php-email-form');
  if (!form) return;

  form.addEventListener('submit', async function (e) {
    e.preventDefault();

    const loading  = form.querySelector('.loading');
    const errorMsg = form.querySelector('.error-message');
    const sentMsg  = form.querySelector('.sent-message');

    loading.classList.add('d-block');
    errorMsg.classList.remove('d-block');
    sentMsg.classList.remove('d-block');

    try {
      const res  = await fetch('/forms/contact.php', {
        method: 'POST',
        body: new FormData(form)
      });
      const text = (await res.text()).trim();

      loading.classList.remove('d-block');

      if (res.ok && text === 'OK') {
        sentMsg.classList.add('d-block');
        form.reset();
      } else {
        throw new Error(text || 'Submission failed. Please try again.');
      }
    } catch (err) {
      loading.classList.remove('d-block');
      errorMsg.textContent = err.message;
      errorMsg.classList.add('d-block');
    }
  });
})();
