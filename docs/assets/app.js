// Lọc + tìm nhanh client-side. Không framework.
(function () {
  var list = document.getElementById('doc-list');
  if (!list) return;

  var cards = Array.prototype.slice.call(list.querySelectorAll('.doc-card'));
  var selLoai = document.getElementById('f-loai');
  var selCoQuan = document.getElementById('f-coquan');
  var selLinhVuc = document.getElementById('f-linhvuc');
  var search = document.getElementById('f-search');
  var reset = document.getElementById('f-reset');
  var count = document.getElementById('f-count');
  var empty = document.getElementById('empty-state');

  function apply() {
    var q = (search.value || '').trim().toLowerCase();
    var shown = 0;
    cards.forEach(function (card) {
      var ok =
        (!selLoai.value || card.dataset.loai === selLoai.value) &&
        (!selCoQuan.value || card.dataset.coquan === selCoQuan.value) &&
        (!selLinhVuc.value || card.dataset.linhvuc === selLinhVuc.value) &&
        (!q || card.dataset.search.indexOf(q) !== -1);
      card.hidden = !ok;
      if (ok) shown++;
    });
    count.textContent = shown === cards.length
      ? cards.length + ' văn bản'
      : shown + ' / ' + cards.length + ' văn bản';
    empty.hidden = shown !== 0;
  }

  [selLoai, selCoQuan, selLinhVuc].forEach(function (el) {
    el.addEventListener('change', apply);
  });
  search.addEventListener('input', apply);
  reset.addEventListener('click', function () {
    selLoai.value = selCoQuan.value = selLinhVuc.value = '';
    search.value = '';
    apply();
  });

  apply();
})();
