(function () {
  "use strict";

  var currentTime = 0;
  var currentDuration = 5;

  function clamp(value, low, high) {
    return Math.min(high, Math.max(low, value));
  }

  function easeOut(value) {
    var x = clamp(value, 0, 1);
    return 1 - Math.pow(1 - x, 3);
  }

  function reveal(element, value) {
    var p = easeOut(value);
    element.style.opacity = String(p);
    element.style.transform = "translateY(" + String((1 - p) * 22) + "px)";
  }

  window.renderAt = function (time, duration) {
    currentTime = Number.isFinite(Number(time)) ? Math.max(0, Number(time)) : 0;
    currentDuration = Number.isFinite(Number(duration)) && Number(duration) > 0
      ? Number(duration)
      : currentDuration;
    var progress = clamp(currentTime / currentDuration, 0, 1);

    document.querySelectorAll("[data-reveal]").forEach(function (element) {
      var delay = Number(element.getAttribute("data-delay") || 0);
      var span = Number(element.getAttribute("data-reveal-span") || 0.55);
      reveal(element, (currentTime - delay) / span);
    });

    document.querySelectorAll("[data-progress]").forEach(function (element) {
      element.style.transform = "scaleX(" + String(progress) + ")";
    });

    document.querySelectorAll("[data-beat-at]").forEach(function (element) {
      var beatAt = Number(element.getAttribute("data-beat-at"));
      if (Number.isFinite(beatAt)) {
        reveal(element, (currentTime - beatAt) / 0.4);
      }
    });
  };

  function renderInitial() {
    window.renderAt(currentTime, currentDuration);
  }

  renderInitial();
  if (document.fonts && document.fonts.ready) {
    document.fonts.ready.then(renderInitial);
  }
})();
