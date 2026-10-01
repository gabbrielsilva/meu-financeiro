(() => {
  const toggle = document.getElementById('menu-toggle');
  const sidebar = document.getElementById('sidebar');
  const close = document.getElementById('menu-close');
  const overlay = document.getElementById('nav-overlay');
  const mobile = window.matchMedia('(max-width: 767px)');
  if (!toggle) return;
  function setOpen(open) {
    document.body.classList.toggle('nav-open', open);
    toggle.setAttribute('aria-expanded', String(open));
    overlay.hidden = !open;
    if (open) requestAnimationFrame(() => close.focus());
  }
  toggle.addEventListener('click', () => setOpen(true));
  close.addEventListener('click', () => { setOpen(false); toggle.focus(); });
  overlay.addEventListener('click', () => { setOpen(false); toggle.focus(); });
  document.addEventListener('keydown', (event) => {
    if (!document.body.classList.contains('nav-open')) return;
    if (event.key === 'Escape') { setOpen(false); toggle.focus(); }
    if (event.key === 'Tab') {
      const items = [...sidebar.querySelectorAll('a, button')].filter(el => el.offsetParent !== null);
      const first = items[0], last = items[items.length - 1];
      if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last.focus(); }
      else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus(); }
    }
  });
  mobile.addEventListener('change', () => setOpen(false));
})();
