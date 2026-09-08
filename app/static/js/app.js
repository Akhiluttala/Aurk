// Resolve independent colour/size controls to the exact existing SKU.
document.querySelectorAll('[data-variant-fields]').forEach(fields => {
  const original = fields.querySelector('[name="variant_id"]');
  const rows = [...original.options].filter(option => option.value);
  const colour = fields.querySelector('[data-colour-select]');
  const size = fields.querySelector('[data-size-select]');
  const form = fields.closest('form');
  function option(text, value) { return new Option(text, value); }
  const colours = new Map(rows.filter(row => !row.disabled).map(row => [row.dataset.colourId, row.dataset.colour]));
  colour.replaceChildren(option('Choose colour', ''));
  colours.forEach((name, id) => colour.add(option(name, id)));
  if (colours.size === 1) colour.value = [...colours.keys()][0];
  function sync() {
    const match = rows.find(row => !row.disabled && row.dataset.colourId === colour.value && row.dataset.sizeId === size.value);
    original.value = match ? match.value : '';
    original.dispatchEvent(new Event('change'));
  }
  function sizes() {
    const previous = size.value;
    size.replaceChildren(option(colour.value ? 'Choose size' : 'Choose colour first', ''));
    const seen = new Set();
    rows.filter(row => row.dataset.colourId === colour.value).forEach(row => {
      if (seen.has(row.dataset.sizeId)) return;
      seen.add(row.dataset.sizeId);
      const entry = option(row.dataset.size + (row.disabled ? ' (Sold out)' : ''), row.dataset.sizeId);
      entry.disabled = row.disabled;
      size.add(entry);
    });
    size.disabled = !colour.value;
    if ([...size.options].some(item => item.value === previous && !item.disabled)) size.value = previous;
    sync();
  }
  colour.required = true;
  size.required = true;
  original.required = false;
  fields.querySelector('[data-combined-label]').hidden = true;
  fields.querySelector('[data-separate-fields]').hidden = false;
  colour.addEventListener('change', sizes);
  size.addEventListener('change', sync);
  form.addEventListener('submit', event => {
    sync();
    if (!original.value) { event.preventDefault(); size.reportValidity(); }
  });
  window.addEventListener('pageshow', sizes);
  sizes();
});

document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('form[data-confirm]').forEach((form) => {
    form.addEventListener('submit', (event) => {
      if (!window.confirm(form.dataset.confirm)) event.preventDefault();
    });
  });

  const mainProductImage = document.getElementById('mainProductImage');
  document.querySelectorAll('[data-product-image]').forEach((thumbnail) => {
    thumbnail.addEventListener('click', () => {
      if (!mainProductImage) return;
      mainProductImage.src = thumbnail.dataset.productImage;
        mainProductImage.alt = thumbnail.querySelector('img')?.alt || 'Product photo';
        const fullImage = document.getElementById('fullProductImage');
        if (fullImage) fullImage.href = thumbnail.dataset.productImage;
      document.querySelectorAll('[data-product-image]').forEach((item) => {
        item.classList.remove('active');
        item.setAttribute('aria-pressed', 'false');
      });
      thumbnail.classList.add('active');
      thumbnail.setAttribute('aria-pressed', 'true');
    });
  });
});


document.querySelectorAll('form[data-submit-once]').forEach((form) => {
  form.addEventListener('submit', () => {
    const button = form.querySelector('button[type="submit"]');
    if (button) { button.disabled = true; button.dataset.label = button.textContent; button.textContent = 'Please wait...'; }
  });
});
window.addEventListener('pageshow', () => {
  document.querySelectorAll('button[data-label]').forEach((button) => {
    button.disabled = false; button.textContent = button.dataset.label;
  });
});
document.querySelectorAll('[data-order-status-url]').forEach((panel) => {
  async function refreshStatus() {
    if (document.hidden) { window.setTimeout(refreshStatus, 15000); return; }
    try {
      const response = await fetch(panel.dataset.orderStatusUrl, { headers: { Accept: 'application/json' } });
      if (!response.ok || !response.headers.get('content-type')?.includes('application/json')) return;
      const data = await response.json();
      panel.querySelector('[data-status-label]').textContent = data.label;
      panel.querySelector('[data-status-message]').textContent = data.message;
      if (['Delivered', 'Cancelled'].includes(data.status)) return;
    } catch (_) { /* The rendered status remains available when offline. */ }
    window.setTimeout(refreshStatus, 15000);
  }
  panel.setAttribute('aria-live', 'polite');
  window.setTimeout(refreshStatus, 15000);
});


document.querySelectorAll('[data-variant-form]').forEach((form) => {
  const select = form.querySelector('[name="variant_id"]');
  const quantity = form.querySelector('[name="quantity"]');
  const price = document.querySelector('[data-variant-price]');
  const stock = form.querySelector('[data-variant-stock]');
  const initialPrice = price.textContent;
  form.querySelectorAll('[data-quantity-step]').forEach(button => {
    button.hidden = false;
    button.addEventListener('click', () => {
      const next = (Number(quantity.value) || 1) + Number(button.dataset.quantityStep);
      quantity.value = String(Math.max(1, Math.min(Number(quantity.max) || 99, next)));
      quantity.dispatchEvent(new Event('change'));
    });
  });
  function updateVariant() {
    const option = select.selectedOptions[0];
    if (!option?.value) {
      price.textContent = initialPrice;
      stock.textContent = 'Choose an option to see availability.';
      quantity.max = '99';
      return;
    }
    const available = Number(option.dataset.stock);
    price.textContent = new Intl.NumberFormat('en-IN', {style: 'currency', currency: 'INR'}).format(Number(option.dataset.price));
    quantity.max = String(available);
    if (Number(quantity.value) > available) quantity.value = String(available);
    stock.textContent = available <= 5 ? `Only ${available} available.` : 'In stock. Ready to order.';
  }
  select.addEventListener('change', updateVariant);
  window.addEventListener('pageshow', updateVariant);
  updateVariant();
});


const menuToggle = document.querySelector('.site-menu-toggle');
const siteHeader = document.querySelector('.site-header');
if (menuToggle && siteHeader) {
  menuToggle.hidden = false;
  siteHeader.dataset.menuOpen = 'false';
  function closeMenu() {
    siteHeader.dataset.menuOpen = 'false';
    menuToggle.setAttribute('aria-expanded', 'false');
  }
  menuToggle.addEventListener('click', () => {
    const open = siteHeader.dataset.menuOpen !== 'true';
    siteHeader.dataset.menuOpen = String(open);
    menuToggle.setAttribute('aria-expanded', String(open));
  });
  siteHeader.addEventListener('keydown', (event) => {
    if (event.key === 'Escape' && siteHeader.dataset.menuOpen === 'true') {
      closeMenu(); menuToggle.focus();
    }
  });
}

// Each card owns its selection/quantity state, including repeated home sections.
document.querySelectorAll('[data-quick-add]').forEach(form => {
  const select = form.querySelector('[name="variant_id"]');
  const quantity = form.querySelector('[name="quantity"]');
  const note = form.querySelector('[data-quick-note]');
  function update() {
    const option = select.selectedOptions[0];
    const available = Number(option?.dataset.stock || 99);
    quantity.max = String(available);
    if (Number(quantity.value) > available) quantity.value = String(available);
    note.textContent = option?.value
      ? `${new Intl.NumberFormat('en-IN', {style:'currency', currency:'INR'}).format(Number(option.dataset.price))} each` + (available <= 5 ? ` / Only ${available} available` : ' / In stock')
      : 'Choose your size to add it straight to your bag.';
  }
  select.addEventListener('change', update);
  window.addEventListener('pageshow', update);
  update();
});
