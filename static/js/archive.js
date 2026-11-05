// Archive: submit the filter form as soon as a dropdown changes.
(function () {
  var form = document.getElementById("filter-form");
  if (!form) return;
  form.querySelectorAll("select").forEach(function (sel) {
    sel.addEventListener("change", function () { form.submit(); });
  });
})();
