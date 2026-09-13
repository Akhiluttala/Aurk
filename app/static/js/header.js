/* Keep layout space stable; reveal the scrolled header by pointer, touch or keyboard. */
(() => {
  const header = document.getElementById('aurk-header');
  const trigger = document.querySelector('.aurk-nav-reveal');
  if (!header || !trigger) return;
  let revealed = false;
  function update() {
    const scrolled = window.scrollY > 140;
    const focused = header.contains(document.activeElement);
    const visible = !scrolled || revealed || focused;
    header.dataset.concealed = String(!visible);
    trigger.hidden = !scrolled || visible;
    trigger.setAttribute('aria-expanded', String(visible));
  }
  function reveal() { revealed = true; update(); }
  trigger.addEventListener('pointerenter', event => {
    if (event.pointerType === 'mouse') reveal();
  });
  trigger.addEventListener('click', () => {
    reveal();
    header.querySelector('a, button').focus({preventScroll:true});
  });
  header.addEventListener('pointerleave', () => { revealed = false; update(); });
  header.addEventListener('focusin', update);
  header.addEventListener('focusout', () => requestAnimationFrame(update));
  window.addEventListener('scroll', () => { revealed = false; update(); }, {passive:true});
  document.addEventListener('keydown', event => {
    if (event.key === 'Escape' && window.scrollY > 140) {
      revealed = false;
      if (header.contains(document.activeElement)) trigger.focus({preventScroll:true});
      update();
    }
  });
  update();
})();
