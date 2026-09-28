/* Progressive enhancement: content remains visible if animation is unavailable. */
(() => {
  if (!document.body.classList.contains('storefront-theme')) return;
  const preference = window.matchMedia('(prefers-reduced-motion: reduce)');
  if (preference.matches || !('IntersectionObserver' in window) || !Element.prototype.animate) return;
  const animations = new Set();
  const menu = document.querySelector('.site-menu-toggle');
  if (menu) menu.addEventListener('click', () => {
    if (preference.matches || menu.getAttribute('aria-expanded') !== 'true') return;
    const navigation = document.getElementById('store-navigation');
    if (!navigation) return;
    const animation = navigation.animate([{opacity:0, transform:'translateY(-6px)'}, {opacity:1, transform:'translateY(0)'}], {duration:220, easing:'ease-out'});
    animations.add(animation);
    animation.onfinish = () => animations.delete(animation);
  });
  const targets = document.querySelectorAll('.storefront-hero-copy, .storefront-hero-feature, .storefront-section-heading, .home-collections > a, .home-product-card, .home-cod-story, .shop-header, .product-card, .commerce-heading');
  const observer = new IntersectionObserver((entries) => {
    entries.forEach((entry, index) => {
      if (!entry.isIntersecting) return;
      observer.unobserve(entry.target);
      if (preference.matches) return;
      const animation = entry.target.animate([
        {opacity:0, transform:'translateY(12px)'},
        {opacity:1, transform:'translateY(0)'}
      ], {duration:480, delay:Math.min(index, 3) * 45, easing:'cubic-bezier(.2,.7,.2,1)', fill:'none'});
      animations.add(animation);
      animation.onfinish = () => animations.delete(animation);
    });
  }, {threshold:0.08});
  targets.forEach((element) => observer.observe(element));
  preference.addEventListener('change', (event) => {
    if (event.matches) { observer.disconnect(); animations.forEach(animation => animation.cancel()); animations.clear(); }
  });
})();
