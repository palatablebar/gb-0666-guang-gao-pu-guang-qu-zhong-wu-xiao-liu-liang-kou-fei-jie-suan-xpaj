const feedback = document.querySelector('#feedback');
async function postJSON(url, body) {
  const response = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  const value = await response.json();
  if (!response.ok) throw new Error(value.detail?.message || value.message || '结算失败，旧版账单保留');
  return value;
}
document.querySelector('#overlap-input')?.addEventListener('submit', async event => {
  event.preventDefault();
  const values = new FormData(event.target);
  try {
    const value = await postJSON('/api/overlap?sample=' + encodeURIComponent(values.get('sample')), {});
    location.href = '/overlap?run_id=' + value.manifest.bill_id;
  } catch (error) {
    feedback.textContent = error.message;
  }
});
document.querySelector('#backfill-form')?.addEventListener('submit', async event => {
  event.preventDefault();
  const form = event.target;
  const text = new FormData(form).get('text');
  if (!text.trim()) {
    feedback.textContent = '请粘贴补数CSV';
    return;
  }
  const button = form.querySelector('button');
  button.disabled = true;
  feedback.textContent = '补数结算中（失败将保留旧版账单）…';
  try {
    const value = await postJSON('/api/overlap/bills/' + form.dataset.bill + '/backfill', { text });
    location.href = '/overlap?run_id=' + value.manifest.bill_id + '&version=' + value.manifest.version;
  } catch (error) {
    feedback.textContent = error.message;
  } finally {
    button.disabled = false;
  }
});
