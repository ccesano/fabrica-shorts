/* paper-collage: seek-safe paper collage animation for HyperFrames. MIT License.
 *
 * Collage.mount(stage) reads a scene's markup (data-* attributes) and returns render(t),
 * a pure function of the scene's local time t in seconds, so the renderer can seek any
 * frame in any order. Collage.scene(id, stageId, duration, speed) wires it to a paused
 * GSAP timeline registered on window.__timelines[id].
 *
 * Markup contract (all times are local content seconds):
 *   .cg-stage[data-seed][data-exit][data-push][data-pushout][data-zoom]
 *   .cg-presenter[data-frames="t:scale,t:scale"]   talking head (img or video), hard punch-in cuts
 *   .cg-strip.cg-label|.cg-word|.cg-tag[data-t]    torn paper strip; its .cg-text types on letter by letter
 *   .cg-doc[data-t][data-rot]                      paper object, drops in from above
 *   .cg-prop / .cg-person / .cg-pop[data-t][data-rot][data-anim="stamp"|"swap"]
 *   .cg-draw[data-t][data-dur]                     SVG whose paths draw on in order
 *   .cg-doodle[data-kind="zzz"|"drops"|"flight"][data-t]
 *   .cg-kin[data-t][data-from]  .cg-count[data-t][data-to]  .cg-fade[data-t]   (fábrica de Shorts)
 *   .cg-stage[data-trans="up|left|right|zoom|cut"][data-outdir][data-shake]
 * Any element may carry data-out to leave earlier than the stage exit (data-exit).
 */
(function () {
  "use strict";

  function clamp01(k) {
    return k < 0 ? 0 : k > 1 ? 1 : k;
  }

  function lerp(a, b, k) {
    return a + (b - a) * k;
  }

  function prog(t, start, dur) {
    if (dur <= 0) return t >= start ? 1 : 0;
    return clamp01((t - start) / dur);
  }

  var ease = {
    outCubic: function (k) { return 1 - Math.pow(1 - clamp01(k), 3); },
    inCubic: function (k) { var c = clamp01(k); return c * c * c; },
    inOutCubic: function (k) {
      var c = clamp01(k);
      return c < 0.5 ? 4 * c * c * c : 1 - Math.pow(-2 * c + 2, 3) / 2;
    },
    outBack: function (k, s) {
      var c = clamp01(k);
      var o = s === undefined ? 1.7 : s;
      return 1 + (o + 1) * Math.pow(c - 1, 3) + o * Math.pow(c - 1, 2);
    },
    inBack: function (k, s) {
      var c = clamp01(k);
      var o = s === undefined ? 1.7 : s;
      return (o + 1) * c * c * c - o * c * c;
    },
  };

  // mulberry32: deterministic 0..1 stream from an integer seed.
  function rng(seed) {
    var a = seed >>> 0;
    return function () {
      a = (a + 0x6d2b79f5) | 0;
      var t = Math.imul(a ^ (a >>> 15), 1 | a);
      t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
      return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };
  }

  function num(el, name, fallback) {
    var v = parseFloat(el.getAttribute(name));
    return isNaN(v) ? fallback : v;
  }

  function px(v) {
    return v.toFixed(1) + "px";
  }

  function each(root, selector, fn) {
    Array.prototype.forEach.call(root.querySelectorAll(selector), fn);
  }

  // Torn paper strip: straight-ish long edges, ragged short ends. Size independent (calc + %).
  function tornClip(seed) {
    var r = rng(seed);
    var pts = [];
    var i;
    pts.push(px(r() * 5) + " " + px(r() * 3));
    for (i = 1; i < 8; i += 1) pts.push(((i / 8) * 100).toFixed(1) + "% " + px(r() * 2.5));
    pts.push("calc(100% - " + px(r() * 5) + ") " + px(r() * 3));
    for (i = 1; i < 7; i += 1) pts.push("calc(100% - " + px(2 + r() * 11) + ") " + ((i / 7) * 100).toFixed(1) + "%");
    pts.push("calc(100% - " + px(r() * 5) + ") calc(100% - " + px(r() * 3) + ")");
    for (i = 7; i > 0; i -= 1) pts.push(((i / 8) * 100).toFixed(1) + "% calc(100% - " + px(r() * 2.5) + ")");
    pts.push(px(r() * 5) + " calc(100% - " + px(r() * 3) + ")");
    for (i = 6; i > 0; i -= 1) pts.push(px(2 + r() * 11) + " " + ((i / 7) * 100).toFixed(1) + "%");
    return "polygon(" + pts.join(", ") + ")";
  }

  // Printed text on a tilted object: tight leading is intentional, and the layout audit
  // measures axis-aligned boxes, which overlap once the object is rotated.
  function allowOverlap(el) {
    each(el, "div, span", function (n) {
      n.setAttribute("data-layout-allow-overlap", "");
    });
  }

  // Split a strip's text into letter spans. Caps get a small ransom-note jitter.
  function splitLetters(textEl, seed, jitter) {
    var r = rng(seed);
    var text = textEl.textContent;
    textEl.textContent = "";
    var letters = [];
    for (var i = 0; i < text.length; i += 1) {
      var ch = text.charAt(i);
      var span = document.createElement("span");
      span.setAttribute("data-layout-allow-overlap", "");
      if (ch === " ") {
        span.textContent = "\u00a0"; // a plain space collapses to nothing inside an inline-block
        span.className = "cg-ch cg-space";
        textEl.appendChild(span);
        continue;
      }
      span.className = "cg-ch";
      span.textContent = ch;
      textEl.appendChild(span);
      letters.push({
        el: span,
        dy: jitter ? (r() - 0.5) * 7 : 0,
        ds: jitter ? 1 + (r() - 0.5) * 0.08 : 1,
        dr: jitter ? (r() - 0.5) * 3 : 0,
      });
    }
    return letters;
  }

  // Letters land one by one (scale 1.8 -> 1), the paper grows with them; on exit the letters
  // delete from the end and the paper collapses.
  function mountStrip(el, index, stageExit, seed) {
    var caps = el.classList.contains("cg-word");
    var paper = el.querySelector(".cg-paper") || el;
    paper.style.clipPath = tornClip(seed + index * 31);
    var letters = splitLetters(el.querySelector(".cg-text"), seed + index * 17, caps);
    var t0 = num(el, "data-t", 0);
    var exitAt = num(el, "data-out", stageExit);
    var n = letters.length;
    var step = num(el, "data-step", n > 16 ? 0.028 : caps ? 0.045 : 0.04);
    var outStep = n > 16 ? 0.012 : 0.022;
    var collapseAt = exitAt + n * outStep + 0.03;
    return function (t) {
      var kin = ease.outCubic(prog(t, t0, 0.14));
      var kout = ease.inCubic(prog(t, collapseAt, 0.12));
      var sx = kin * (1 - kout);
      el.style.opacity = sx > 0.001 ? "1" : "0";
      el.style.transform = "rotate(" + num(el, "data-rot", 0).toFixed(2) + "deg) scaleX(" + sx.toFixed(4) + ")";
      for (var i = 0; i < n; i += 1) {
        var L = letters[i];
        var p = prog(t, t0 + 0.1 + i * step, 0.16);
        var q = prog(t, exitAt + (n - 1 - i) * outStep, 0.09);
        var s = lerp(1.8, 1, ease.outCubic(p)) * lerp(1, 0.2, ease.inCubic(q)) * L.ds;
        var o = clamp01(p * 5) * (1 - q);
        var y = lerp(-14, 0, ease.outCubic(p)) + L.dy;
        L.el.style.opacity = o.toFixed(3);
        L.el.style.transform = "translateY(" + px(y) + ") rotate(" + L.dr.toFixed(2) + "deg) scale(" + s.toFixed(4) + ")";
      }
    };
  }

  // Paper document: drops in from above with a settle, sways a hair while held, pops out.
  function mountDoc(el, stageExit, seed) {
    allowOverlap(el);
    var t0 = num(el, "data-t", 0);
    var rot = num(el, "data-rot", 0);
    var exitAt = num(el, "data-out", stageExit);
    var phase = rng(seed)() * 6.28;
    return function (t) {
      var p = prog(t, t0, 0.42);
      var q = prog(t, exitAt + 0.12, 0.22);
      var y = lerp(-900, 0, ease.outBack(p, 1.15));
      var r = lerp(rot - 16, rot, ease.outCubic(p)) + 0.5 * Math.sin(t * 1.3 + phase) + 12 * ease.inCubic(q);
      var s = 1 - ease.inBack(q, 1.4);
      el.style.opacity = p > 0 && s > 0.001 ? "1" : "0";
      el.style.transform = "translateY(" + px(y) + ") rotate(" + r.toFixed(2) + "deg) scale(" + Math.max(0, s).toFixed(4) + ")";
    };
  }

  // Cutout sticker, person, or any small pop element. data-anim="stamp" slams down instead,
  // data-anim="swap" just cuts in (a phone screen changing).
  function mountSticker(el, stageExit, seed, kind) {
    allowOverlap(el);
    var person = kind === "person";
    var stamp = el.getAttribute("data-anim") === "stamp";
    var swap = el.getAttribute("data-anim") === "swap";
    var t0 = num(el, "data-t", 0);
    var rot = num(el, "data-rot", 0);
    var exitAt = num(el, "data-out", stageExit);
    var phase = rng(seed)() * 6.28;
    var wobble = kind === "pop" ? 0 : 0.6;
    var inDur = person ? 0.34 : stamp ? 0.2 : swap ? 0.1 : 0.3;
    var outAt = exitAt + (person ? 0.16 : 0.06);
    return function (t) {
      var p = prog(t, t0, inDur);
      var q = prog(t, outAt, 0.22);
      var sIn = swap ? 1 : person ? lerp(0.5, 1, ease.outBack(p, 1.8)) : stamp ? lerp(2.4, 1, ease.outCubic(p)) : ease.outBack(p, 2.2);
      var s = sIn * (1 - ease.inBack(q, 1.4));
      var y = person ? lerp(40, 0, ease.outCubic(p)) : 0;
      var r = (person || stamp || swap ? rot : lerp(rot - 30, rot, ease.outCubic(p))) + wobble * Math.sin(t * 1.1 + phase);
      var o = swap ? p : person ? clamp01(p * 6) : stamp ? clamp01(p * 3) : 1;
      el.style.opacity = p > 0 && s > 0.001 ? o.toFixed(3) : "0";
      el.style.transform = "translateY(" + px(y) + ") rotate(" + r.toFixed(2) + "deg) scale(" + Math.max(0, s).toFixed(4) + ")";
    };
  }

  // Hand-drawn marks: every path in the SVG draws on in order over data-dur seconds.
  function mountDraw(el, stageExit) {
    var t0 = num(el, "data-t", 0);
    var dur = num(el, "data-dur", 0.35);
    var exitAt = num(el, "data-out", stageExit);
    var paths = Array.prototype.slice.call(el.querySelectorAll("path"));
    var lens = null;
    return function (t) {
      if (!lens) {
        lens = paths.map(function (p) { return p.getTotalLength(); });
        paths.forEach(function (p, i) { p.style.strokeDasharray = lens[i].toFixed(1); });
      }
      var n = paths.length;
      for (var i = 0; i < n; i += 1) {
        var k = ease.outCubic(prog(t, t0 + (i * dur) / n, dur / n));
        paths[i].style.strokeDashoffset = (lens[i] * (1 - k)).toFixed(1);
      }
      var f = 1 - prog(t, exitAt, 0.16);
      el.style.opacity = (t >= t0 ? f : 0).toFixed(3);
    };
  }

  // Doodles: small hand-made accents. zzz floats up, drops bob, flight draws a dashed route
  // with a paper plane riding its tip.
  function mountDoodle(el, stageExit) {
    var kind = el.getAttribute("data-kind");
    var t0 = num(el, "data-t", 0);
    var exitAt = num(el, "data-out", stageExit);
    var fade = function (t) { return 1 - prog(t, exitAt, 0.18); };

    if (kind === "flight") {
      var path = el.querySelector(".cg-route");
      var mask = el.querySelector(".cg-route-mask");
      var plane = el.querySelector(".cg-plane");
      var total = 0;
      return function (t) {
        if (!total) {
          total = path.getTotalLength();
          mask.style.strokeDasharray = total.toFixed(1);
        }
        var k = ease.inOutCubic(prog(t, t0, 1.2));
        mask.style.strokeDashoffset = (total * (1 - k)).toFixed(1);
        var a = path.getPointAtLength(total * k);
        var b = path.getPointAtLength(Math.min(total, total * k + 2));
        var ang = (Math.atan2(b.y - a.y, b.x - a.x) * 180) / Math.PI;
        var ps = ease.outBack(prog(t, t0, 0.2), 2);
        el.style.opacity = (t >= t0 ? fade(t) : 0).toFixed(3);
        plane.setAttribute("transform", "translate(" + a.x.toFixed(1) + " " + a.y.toFixed(1) + ") rotate(" + ang.toFixed(1) + ") scale(" + ps.toFixed(3) + ")");
      };
    }

    var parts = Array.prototype.slice.call(el.querySelectorAll(".cg-bit"));
    var gap = kind === "zzz" ? 0.24 : 0.14;
    return function (t) {
      var f = fade(t);
      for (var i = 0; i < parts.length; i += 1) {
        var ti = t0 + i * gap;
        var p = prog(t, ti, 0.26);
        var s = ease.outBack(p, 2.4) * (0.4 + 0.6 * f);
        var held = Math.max(0, t - ti - 0.26);
        var y = kind === "zzz" ? -22 * held : 10 * Math.sin(held * 2.2 + i);
        var r = kind === "zzz" ? 6 * Math.sin(held * 1.8 + i * 1.3) : 0;
        parts[i].style.opacity = (p > 0 ? f : 0).toFixed(3);
        parts[i].style.transform = "translateY(" + px(y) + ") rotate(" + r.toFixed(2) + "deg) scale(" + s.toFixed(4) + ")";
      }
    };
  }

  // Talking head (still image or retimed video): hard punch-in cuts at the listed times
  // plus a slow push.
  function mountPresenter(el) {
    var keys = (el.getAttribute("data-frames") || "0:1").split(",").map(function (s) {
      var kv = s.split(":");
      return [parseFloat(kv[0]), parseFloat(kv[1])];
    });
    return function (t) {
      var s = keys[0][1];
      for (var i = 0; i < keys.length; i += 1) if (t >= keys[i][0]) s = keys[i][1];
      s *= 1 + 0.0025 * t;
      el.style.transform = "scale(" + s.toFixed(4) + ")";
    };
  }


  // ── fábrica: tipografía cinética, contador y fundidos ──
  // Palabra gigante que golpea (escala 1.7 → 1 con desenfoque); cada golpe sacude el mundo.
  function mountKin(el, stageExit, seed, hits) {
    allowOverlap(el);
    var t0 = num(el, "data-t", 0);
    var exitAt = num(el, "data-out", stageExit);
    var rot = num(el, "data-rot", 0);
    var from = el.getAttribute("data-from") || "zoom";
    hits.push(t0 + 0.12);
    return function (t) {
      var p = prog(t, t0, 0.24);
      var q = prog(t, exitAt, 0.18);
      var k = ease.outBack(p, 1.25);
      var s = from === "zoom" ? lerp(1.7, 1, k) : 1;
      var x = from === "left" ? lerp(-1200, 0, ease.outCubic(p)) : from === "right" ? lerp(1200, 0, ease.outCubic(p)) : 0;
      var y = from === "up" ? lerp(-260, 0, k) : from === "down" ? lerp(260, 0, k) : 0;
      x += lerp(0, -1300, ease.inCubic(q));
      var blur = (1 - clamp01(p * 1.6)) * 10;
      el.style.opacity = p > 0 && q < 1 ? clamp01(p * 4).toFixed(3) : "0";
      el.style.filter = blur > 0.05 ? "blur(" + blur.toFixed(2) + "px)" : "none";
      el.style.transform = "translate(" + px(x) + "," + px(y) + ") rotate(" + rot.toFixed(2) + "deg) scale(" + s.toFixed(4) + ")";
    };
  }

  // Número que cuenta hasta su valor y queda latiendo.
  function mountCount(el, stageExit, hits) {
    var t0 = num(el, "data-t", 0);
    var dur = num(el, "data-dur", 1.2);
    var a = num(el, "data-from", 0), b = num(el, "data-to", 100);
    var dec = num(el, "data-dec", 0);
    var sep = el.getAttribute("data-sep") || ".";
    var pre = el.getAttribute("data-pre") || "", suf = el.getAttribute("data-suf") || "";
    var exitAt = num(el, "data-out", stageExit);
    var target = el.querySelector(".cg-num") || el;
    hits.push(t0 + dur);
    function fmt(v) {
      var s = v.toFixed(dec), parts = s.split(".");
      parts[0] = parts[0].replace(/\B(?=(\d{3})+(?!\d))/g, sep);
      return pre + parts.join(sep === "." ? "," : ".") + suf;
    }
    return function (t) {
      var p = prog(t, t0, dur);
      var q = prog(t, exitAt, 0.2);
      var v = lerp(a, b, ease.outCubic(p));
      target.textContent = fmt(p >= 1 ? b : v);
      var land = prog(t, t0 + dur, 0.25);
      var s = (t < t0 ? 0 : lerp(0.85, 1, ease.outCubic(prog(t, t0, 0.2)))) * (1 + 0.08 * Math.sin(Math.PI * land)) * (1 - ease.inBack(q, 1.4));
      el.style.opacity = t >= t0 && s > 0.001 ? "1" : "0";
      el.style.transform = "scale(" + Math.max(0, s).toFixed(4) + ")";
    };
  }

  // Aparición suave (palabras de una cita, subtítulos internos): sube y se enfoca.
  function mountFade(el, stageExit) {
    var t0 = num(el, "data-t", 0);
    var exitAt = num(el, "data-out", stageExit);
    var d = num(el, "data-dur", 0.22);
    return function (t) {
      var p = ease.outCubic(prog(t, t0, d));
      var q = prog(t, exitAt, 0.18);
      el.style.opacity = (p * (1 - q)).toFixed(3);
      el.style.transform = "translateY(" + px(lerp(24, 0, p)) + ")";
      el.style.filter = p < 0.99 ? "blur(" + ((1 - p) * 6).toFixed(2) + "px)" : "none";
    };
  }

  function mount(stage) {
    var seed = num(stage, "data-seed", 1);
    var exitAt = num(stage, "data-exit", 999);
    var push = stage.getAttribute("data-push") === "1";
    var pushOut = num(stage, "data-pushout", -1);
    var world = stage.querySelector(".cg-world");
    var zoom = num(stage, "data-zoom", 0.03);
    var parts = [];
    var hits = [];
    var trans = stage.getAttribute("data-trans") || "up";
    var outDir = stage.getAttribute("data-outdir") || "up";
    var shakeAmp = num(stage, "data-shake", 16);

    each(stage, ".cg-presenter", function (el) { parts.push(mountPresenter(el)); });
    each(stage, ".cg-strip", function (el, i) { parts.push(mountStrip(el, i, exitAt, seed)); });
    each(stage, ".cg-doc", function (el, i) { parts.push(mountDoc(el, exitAt, seed + 101 + i)); });
    each(stage, ".cg-prop", function (el, i) { parts.push(mountSticker(el, exitAt, seed + 201 + i, "prop")); });
    each(stage, ".cg-person", function (el, i) { parts.push(mountSticker(el, exitAt, seed + 301 + i, "person")); });
    each(stage, ".cg-pop", function (el, i) { parts.push(mountSticker(el, exitAt, seed + 401 + i, "pop")); });
    each(stage, ".cg-draw", function (el) { parts.push(mountDraw(el, exitAt)); });
    each(stage, ".cg-doodle", function (el) { parts.push(mountDoodle(el, exitAt)); });
    each(stage, ".cg-kin", function (el, i) { parts.push(mountKin(el, exitAt, seed + 501 + i, hits)); });
    each(stage, ".cg-count", function (el) { parts.push(mountCount(el, exitAt, hits)); });
    each(stage, ".cg-fade", function (el) { parts.push(mountFade(el, exitAt)); });

    function shake(t) {
      var x = 0, y = 0;
      for (var i = 0; i < hits.length; i += 1) {
        var d = t - hits[i];
        if (d < 0 || d > 0.35) continue;
        var a = shakeAmp * Math.exp(-d * 14);
        x += a * Math.sin(d * 95 + i);
        y += a * 0.7 * Math.cos(d * 80 + i * 2);
      }
      return [x, y];
    }

    return function render(t) {
      var k = ease.inOutCubic(prog(t, 0, 0.4));
      var tx = 0, ty = 0, sc = 1, op = 1;
      if (push) {
        if (trans === "left") tx = lerp(1080, 0, k);
        else if (trans === "right") tx = lerp(-1080, 0, k);
        else if (trans === "zoom") { sc = lerp(1.35, 1, ease.outCubic(prog(t, 0, 0.35))); op = clamp01(prog(t, 0, 0.18)); }
        else if (trans === "cut") { op = t >= 0 ? 1 : 0; }
        else ty = lerp(1920, 0, k);
      }
      if (pushOut >= 0) {
        var o = ease.inOutCubic(prog(t, pushOut, 0.4));
        if (outDir === "left") tx += lerp(0, -420, o);
        else if (outDir === "right") tx += lerp(0, 420, o);
        else if (outDir === "zoom") sc *= lerp(1, 0.86, o);
        else if (outDir === "cut") { }
        else ty += lerp(0, -520, o);
      }
      stage.style.opacity = op.toFixed(3);
      stage.style.transform = "translate(" + px(tx) + "," + px(ty) + ") scale(" + sc.toFixed(4) + ")";
      var sh = shake(t);
      if (world) world.style.transform = "translate(" + px(sh[0]) + "," + px(sh[1]) + ") scale(" + (1 + zoom * prog(t, 0.4, 6)).toFixed(4) + ")";
      for (var i = 0; i < parts.length; i += 1) parts[i](t);
    };
  }

  // Wire one scene: build render(t) and register its paused timeline under `id`.
  // `duration` is in content seconds; with `speed` > 1 the scene plays faster (real length
  // duration / speed) while render(t) keeps receiving content time.
  function scene(id, stageId, duration, speed) {
    speed = speed || 1;
    var stage = document.getElementById(stageId);
    var render = mount(stage);
    var tl = gsap.timeline({ paused: true });
    var driver = { t: 0 };
    tl.to(driver, { t: duration, duration: duration / speed, ease: "none", onUpdate: function () { render(driver.t); } }, 0);
    render(0);
    window.__timelines = window.__timelines || {};
    window.__timelines[id] = tl;
  }

  window.Collage = { mount: mount, scene: scene, rng: rng, tornClip: tornClip };
})();
