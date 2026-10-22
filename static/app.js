const tg = window.Telegram?.WebApp;
if (tg) { tg.ready(); tg.expand(); }

const backdrop = document.getElementById('modalBackdrop');
const modalBody = document.getElementById('modalBody');
const modalMessage = document.getElementById('modalMessage');
const modalClose = document.getElementById('modalClose');
const toast = document.getElementById('toast');
let registrationPoll = null;
let toastTimer = null;

function som(value) { return `${Number(value || 0).toLocaleString('uz-UZ').replace(/\u00a0/g, ' ')} so‘m`; }
function showToast(message) {
  toast.textContent = message;
  toast.classList.add('show');
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => toast.classList.remove('show'), 3600);
}
function showModal(content) {
  modalBody.innerHTML = content;
  modalMessage.textContent = '';
  modalMessage.classList.remove('error');
  backdrop.hidden = false;
  document.body.style.overflow = 'hidden';
}
function closeModal() {
  backdrop.hidden = true;
  document.body.style.overflow = '';
  modalMessage.textContent = '';
}
modalClose.addEventListener('click', closeModal);
backdrop.addEventListener('click', e => { if (e.target === backdrop) closeModal(); });
document.addEventListener('keydown', e => { if (e.key === 'Escape' && !backdrop.hidden) closeModal(); });

function setMessage(message, error = false) {
  modalMessage.classList.toggle('error', error);
  modalMessage.innerHTML = message;
}
async function api(url, options = {}) {
  const response = await fetch(url, { credentials: 'same-origin', ...options, headers: { 'Content-Type': 'application/json', ...(options.headers || {}) } });
  let data = {};
  try { data = await response.json(); } catch (_) {}
  if (!response.ok) throw new Error(data.detail || data.message || 'So‘rovni bajarib bo‘lmadi.');
  return data;
}

function orderForm() {
  showModal(`<h2 id="modalTitle">Buyurtma berish</h2><p class="modal-subtitle">Vazifani tushuntiring. Buyurtma sayt va Telegram botdagi ijrochilarga ko‘rinadi.</p>
    <form id="orderForm"><label class="field"><span>Buyurtma tavsifi</span><textarea name="description" required minlength="5" maxlength="1000" placeholder="Masalan: 10 slaydli, zamonaviy prezentatsiya kerak"></textarea></label>
    <label class="field"><span>Budjet (so‘m)</span><input name="price" type="number" min="1000" max="100000000" step="1000" required placeholder="30000"></label>
    <label class="field"><span>Aloqa uchun Telegram username yoki telefon</span><input name="contact" required minlength="3" maxlength="100" placeholder="@username yoki +998…"></label>
    <button class="btn btn-primary modal-submit" type="submit">Buyurtmani yuborish ↗</button></form><p class="modal-note">Buyurtmani yuborish uchun ijrochi akkaunti shart emas. Aloqa ma’lumotini to‘g‘ri kiriting.</p>`);
  document.getElementById('orderForm').addEventListener('submit', async e => {
    e.preventDefault();
    const form = new FormData(e.currentTarget);
    const button = e.currentTarget.querySelector('button[type="submit"]');
    button.disabled = true; button.textContent = 'Yuborilmoqda…';
    try {
      const result = await api('/api/orders', { method: 'POST', body: JSON.stringify({ description: form.get('description').trim(), price: Number(form.get('price')), contact: form.get('contact').trim() }) });
      setMessage(`✅ Buyurtma #${result.order_id} qabul qilindi. Narxi: <strong>${som(result.price)}</strong>.`);
      e.currentTarget.reset();
      loadOrders();
      showToast('Buyurtma muvaffaqiyatli yuborildi!');
      setTimeout(closeModal, 2400);
    } catch (err) { setMessage(err.message, true); }
    finally { button.disabled = false; button.textContent = 'Buyurtmani yuborish ↗'; }
  });
}

function registerForm() {
  showModal(`<h2 id="modalTitle">Ijrochi akkauntini yarating</h2><p class="modal-subtitle">Sayt va Telegram bot uchun bitta akkaunt. Bir martalik faollashtirish to‘lovi: <strong>4 000 so‘m</strong>, faqat Telegram orqali.</p>
    <form id="registerForm"><label class="field"><span>Yangi login</span><input name="username" required minlength="3" maxlength="32" pattern="[A-Za-z0-9_.-]+" autocomplete="username" placeholder="masalan, jasur_01"></label>
    <label class="field"><span>Parol (kamida 8 belgi)</span><input name="password" type="password" required minlength="8" maxlength="128" autocomplete="new-password" placeholder="Kuchli parol yarating"></label>
    <button class="btn btn-primary modal-submit" type="submit">Telegram’da davom etish ↗</button></form>
    <p class="modal-note">Keyingi qadamda Telegram bot ochiladi. To‘lov chekini botga yuboring. Admin haqiqiy to‘lovni tekshirgach, akkaunt avtomatik faollashadi. Parolingizni hech kimga bermang.</p>`);
  document.getElementById('registerForm').addEventListener('submit', async e => {
    e.preventDefault();
    const form = new FormData(e.currentTarget);
    const button = e.currentTarget.querySelector('button[type="submit"]');
    button.disabled = true; button.textContent = 'Akkaunt yaratilmoqda…';
    try {
      const result = await api('/api/register', { method: 'POST', body: JSON.stringify({ username: form.get('username').trim(), password: form.get('password') }) });
      if (!result.telegram_url || result.telegram_url === 'https://t.me/') {
        setMessage('Akkaunt yaratildi, ammo bot manzili serverda sozlanmagan. Render Environment bo‘limiga BOT_USERNAME qiymatini qo‘shish kerak.', true);
        return;
      }
      setMessage(`Login <strong>${escapeHtml(result.username || form.get('username'))}</strong> yaratildi. Telegram botda to‘lovni yakunlang. Shu oynani ochiq qoldiring — tasdiqlangach saytga avtomatik kirasiz. <br><br><a href="${result.telegram_url}" target="_blank" rel="noopener">Telegram botni ochish ↗</a>`);
      window.open(result.telegram_url, '_blank', 'noopener');
      const linkToken = result.link_token;
      if (registrationPoll) clearInterval(registrationPoll);
      let attempts = 0;
      registrationPoll = setInterval(async () => {
        attempts++;
        if (attempts > 120) { clearInterval(registrationPoll); registrationPoll = null; return; }
        try {
          const status = await api(`/api/worker/status?link_token=${encodeURIComponent(linkToken)}`);
          if (status.active) {
            clearInterval(registrationPoll); registrationPoll = null;
            setMessage(`🎉 To‘lov tasdiqlandi! <strong>${escapeHtml(status.username)}</strong> akkauntingiz faollashdi. Saytga kirdingiz.`);
            showToast('Ijrochi akkauntingiz faollashdi!');
            setTimeout(() => { closeModal(); updateNav(); loadOrders(); }, 2200);
          }
        } catch (_) {}
      }, 5000);
    } catch (err) { setMessage(err.message, true); }
    finally { button.disabled = false; button.textContent = 'Telegram’da davom etish ↗'; }
  });
}

function loginForm() {
  showModal(`<h2 id="modalTitle">Xush kelibsiz</h2><p class="modal-subtitle">Faollashtirilgan ijrochi akkauntingiz bilan kiring.</p>
    <form id="loginForm"><label class="field"><span>Login</span><input name="username" required autocomplete="username" placeholder="Login"></label><label class="field"><span>Parol</span><input name="password" type="password" required autocomplete="current-password" placeholder="Parol"></label><button class="btn btn-primary modal-submit" type="submit">Kirish →</button></form>
    <p class="modal-note">Yangi akkaunt kerakmi? <button type="button" id="switchRegister">Ro‘yxatdan o‘tish</button></p>`);
  document.getElementById('switchRegister').addEventListener('click', registerForm);
  document.getElementById('loginForm').addEventListener('submit', async e => {
    e.preventDefault();
    const form = new FormData(e.currentTarget);
    const button = e.currentTarget.querySelector('button[type="submit"]'); button.disabled = true; button.textContent = 'Tekshirilmoqda…';
    try {
      const result = await api('/api/login', { method: 'POST', body: JSON.stringify({ username: form.get('username').trim(), password: form.get('password') }) });
      setMessage(`Salom, <strong>${escapeHtml(result.username)}</strong>! Saytga muvaffaqiyatli kirdingiz.`);
      showToast('Kirish muvaffaqiyatli');
      setTimeout(() => { closeModal(); updateNav(); loadOrders(); }, 1000);
    } catch (err) { setMessage(err.message, true); }
    finally { button.disabled = false; button.textContent = 'Kirish →'; }
  });
}

function adminForm() {
  showModal(`<h2 id="modalTitle">Admin panel</h2><p class="modal-subtitle">Administrator hisob ma’lumotlarini kiriting.</p><form id="adminForm"><label class="field"><span>Admin login</span><input name="username" required autocomplete="username"></label><label class="field"><span>Admin parol</span><input name="password" type="password" required autocomplete="current-password"></label><button class="btn btn-primary modal-submit" type="submit">Admin sifatida kirish</button></form>`);
  document.getElementById('adminForm').addEventListener('submit', async e => {
    e.preventDefault(); const form = new FormData(e.currentTarget); const button = e.currentTarget.querySelector('button'); button.disabled = true;
    try {
      await api('/api/admin/login', { method: 'POST', body: JSON.stringify({ username: form.get('username'), password: form.get('password') }) });
      const result = await api('/api/admin/orders');
      modalBody.innerHTML = `<h2 id="modalTitle">Admin panel</h2><p class="modal-subtitle">So‘nggi buyurtmalar: ${result.orders.length} ta</p><div class="admin-list">${result.orders.map(o => `<div class="admin-row"><strong>#${o.id} · ${som(o.price)}</strong>${escapeHtml(o.description)}<br>Holat: ${escapeHtml(o.status)} · Manba: ${escapeHtml(o.source || 'telegram')}<br>Aloqa: ${escapeHtml(o.contact || 'Telegram orqali')}</div>`).join('') || '<p class="modal-note">Hozircha buyurtmalar yo‘q.</p>'}</div><button class="btn btn-outline modal-submit" id="adminRefresh">↻ Yangilash</button>`;
      document.getElementById('adminRefresh').addEventListener('click', adminForm);
    } catch (err) { setMessage(err.message, true); }
    finally { button.disabled = false; }
  });
}

function escapeHtml(value) { return String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c])); }

async function loadOrders() {
  const grid = document.getElementById('ordersGrid');
  try {
    const result = await api('/api/orders');
    if (!result.orders.length) {
      grid.innerHTML = `<div class="empty-state"><span>✦</span><p>Hozircha ochiq buyurtmalar yo‘q. Birinchi buyurtmani siz joylashtiring.</p></div>`;
      return;
    }
    grid.innerHTML = result.orders.map(order => `<article class="order-card"><div class="order-card-top"><span class="order-number">BUYURTMA #${order.id}</span><span class="order-status">● Ochiq</span></div><h3>${escapeHtml(order.description)}</h3><p>Ijrochi qidirilmoqda. Buyurtma tafsilotlarini ko‘rib, uni olish uchun akkauntingizga kiring.</p><div class="order-card-bottom"><span class="price">${som(order.price)}</span><button class="take-order" data-take="${order.id}">Buyurtmani olish ↗</button></div></article>`).join('');
    grid.querySelectorAll('[data-take]').forEach(button => button.addEventListener('click', () => takeOrder(button.dataset.take, button)));
  } catch (err) { grid.innerHTML = `<div class="empty-state"><p>Buyurtmalarni yuklab bo‘lmadi. Birozdan keyin qayta urinib ko‘ring.</p></div>`; }
}

async function takeOrder(id, button) {
  button.disabled = true;
  try {
    const result = await api(`/api/orders/${id}/take`, { method: 'POST', body: '{}' });
    showToast((result.message || 'Buyurtma olindi') + (result.contact ? ` Aloqa: ${result.contact}` : ''));
    loadOrders();
  } catch (err) {
    if (err.message.includes('kiring') || err.message.includes('faollashtirilmagan')) loginForm();
    else showToast(err.message);
  } finally { button.disabled = false; }
}

async function updateNav() {
  try {
    const me = await api('/api/me');
    const login = document.getElementById('loginOpen');
    const register = document.getElementById('registerOpen');
    if (me.logged_in) {
      login.textContent = `Salom, ${me.username}`;
      register.textContent = 'Chiqish';
      register.onclick = async () => { await api('/api/logout', { method: 'POST', body: '{}' }); showToast('Akkauntdan chiqdingiz'); updateNav(); };
    } else {
      login.textContent = 'Kirish'; register.textContent = 'Ro‘yxatdan o‘tish ↗'; register.onclick = registerForm;
    }
  } catch (_) {}
}

document.getElementById('loginOpen').addEventListener('click', loginForm);
document.getElementById('registerOpen').onclick = registerForm;
document.getElementById('adminOpen').addEventListener('click', adminForm);
document.getElementById('heroOrder').addEventListener('click', orderForm);
document.getElementById('ctaOrder').addEventListener('click', orderForm);
document.getElementById('ctaRegister').addEventListener('click', registerForm);
document.getElementById('refreshOrders').addEventListener('click', loadOrders);
document.getElementById('mobileMenu').addEventListener('click', () => document.querySelector('.nav-links').classList.toggle('open'));
document.querySelectorAll('.nav-links a').forEach(a => a.addEventListener('click', () => document.querySelector('.nav-links').classList.remove('open')));

loadOrders();
updateNav();
