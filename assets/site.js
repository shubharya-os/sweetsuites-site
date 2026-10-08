// Sweet Suites site: nav border on scroll, FAQ deep links, greyscale preview. No libraries, no network, no storage.
(function () {
  var nav = document.getElementById('nav');
  if (nav) {
    var onScroll = function () { nav.classList.toggle('scrolled', window.scrollY > 8); };
    onScroll();
    window.addEventListener('scroll', onScroll, { passive: true });
  }

  // Open the FAQ answer a link points at (e.g. support.html#restore).
  function openFromHash() {
    if (!location.hash) return;
    var el = document.getElementById(decodeURIComponent(location.hash.slice(1)));
    if (el && el.tagName === 'DETAILS') { el.open = true; el.scrollIntoView(); }
  }
  openFromHash();
  window.addEventListener('hashchange', openFromHash);

  // Greyscale preview of the car colours: the roof symbols still tell them apart.
  var toggle = document.getElementById('gray-toggle');
  var fleet = document.getElementById('fleet');
  if (toggle && fleet) {
    toggle.addEventListener('change', function () { fleet.classList.toggle('gray', toggle.checked); });
  }
})();
