/* Session trials live in sessionStorage. A new successful load sets
   data-clear-trials="1" once; a refresh posts the stored tray back. */
(function () {
  var KEY = "pch1.trials";
  var EMPTY_STOCKOUTS = "No projected stockouts on PCH1 for this horizon.";
  var form = document.getElementById("trial-form");
  var list = document.getElementById("trials");
  var errorNode = document.getElementById("trial-error");

  if (document.body.getAttribute("data-clear-trials") === "1") {
    sessionStorage.removeItem(KEY);
  }

  function readJsonAttr(name) {
    var raw = document.body.getAttribute(name);
    if (!raw) return null;
    try {
      return JSON.parse(raw);
    } catch (err) {
      return null;
    }
  }

  function readTrials() {
    try {
      var parsed = JSON.parse(sessionStorage.getItem(KEY) || "[]");
      if (!Array.isArray(parsed)) return [];
      return parsed.filter(function (trial) {
        return trial && trial.sku && trial.week && trial.cases !== undefined && trial.cases !== null;
      });
    } catch (err) {
      return [];
    }
  }

  function writeTrials(trials) {
    sessionStorage.setItem(KEY, JSON.stringify(trials));
  }

  function fmt(value) {
    var n = Number(value);
    if (!Number.isFinite(n)) return "";
    var rounded = Math.round(n);
    if (Math.abs(n - rounded) < 1e-9) return String(rounded);
    return String(n);
  }

  function el(tag, className, text) {
    var node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined && text !== null) node.textContent = text;
    return node;
  }

  function showError(message) {
    if (!errorNode) return;
    errorNode.hidden = !message;
    errorNode.textContent = message || "";
  }

  function fillSelect(select, values) {
    if (!select || !Array.isArray(values) || !values.length) return;
    var current = select.value;
    select.replaceChildren();
    values.forEach(function (value) {
      var option = document.createElement("option");
      option.value = String(value);
      option.textContent = String(value);
      select.appendChild(option);
    });
    if (values.map(String).indexOf(current) !== -1) select.value = current;
  }

  function seriesByPart(series) {
    var map = {};
    (series || []).forEach(function (row) {
      map[row.part] = row;
    });
    return map;
  }

  function weekTable(series) {
    var table = el("table", "weeks");
    var head = document.createElement("thead");
    var titles = document.createElement("tr");
    ["Week", "Forecast", "Production", "Trials", "Stock"].forEach(function (label) {
      titles.appendChild(el("th", "", label));
    });
    head.appendChild(titles);
    table.appendChild(head);
    var body = document.createElement("tbody");
    series.weeks.forEach(function (week, index) {
      var row = document.createElement("tr");
      [week, fmt(series.forecast[index]), fmt(series.production[index]), fmt(series.trials[index])].forEach(function (text) {
        row.appendChild(el("td", "", text));
      });
      var stock = el("td", Number(series.stock[index]) < 0 ? "neg" : "", fmt(series.stock[index]));
      row.appendChild(stock);
      body.appendChild(row);
    });
    table.appendChild(body);
    return table;
  }

  function rail(weeks, mark, kind) {
    var cells = el("ol", "rail");
    weeks.forEach(function (week) {
      var marked = week === mark;
      var cell = el("li", "rail-cell" + (marked ? " " + kind : ""));
      cell.title = week;
      var note = week;
      if (marked) note += kind === "is-break" ? " first stockout" : " cover";
      cell.appendChild(el("span", "sr", note));
      cells.appendChild(cell);
    });
    return cells;
  }

  function exceptionRow(row, byPart, weeks, kind) {
    var stockout = kind === "stockout";
    var details = el("details", stockout ? "exception" : "exception cover-row");
    var summary = document.createElement("summary");
    var identity = el("span", "identity");
    identity.appendChild(el("span", "part", row.part));
    identity.appendChild(el("span", "desc", row.description));
    summary.appendChild(identity);
    summary.appendChild(el("span", "when num", row.week));
    summary.appendChild(el(
      "span",
      "gap num",
      stockout ? fmt(row.cases_short) + " short" : fmt(row.cover_weeks) + " wk"
    ));
    summary.appendChild(rail(weeks, row.week, stockout ? "is-break" : "is-cover"));
    details.appendChild(summary);
    if (byPart[row.part]) details.appendChild(weekTable(byPart[row.part]));
    return details;
  }

  function replaceRows(section, items, emptyText) {
    if (!section) return;
    Array.prototype.slice.call(section.children).forEach(function (node) {
      if (node.classList.contains("rows") || node.classList.contains("empty")) node.remove();
    });
    if (!items.length) {
      if (emptyText) section.appendChild(el("p", "empty", emptyText));
      return;
    }
    var wrap = el("div", "rows");
    items.forEach(function (item) { wrap.appendChild(item); });
    section.appendChild(wrap);
  }

  function paintBoard(data) {
    var weeks = data.weeks || [];
    var byPart = seriesByPart(data.series);
    replaceRows(
      document.querySelector(".exceptions"),
      (data.stockouts || []).map(function (row) {
        return exceptionRow(row, byPart, weeks, "stockout");
      }),
      EMPTY_STOCKOUTS
    );
    replaceRows(
      document.querySelector(".cover-block"),
      (data.cover || []).map(function (row) {
        return exceptionRow(row, byPart, weeks, "cover");
      }),
      ""
    );
  }

  function renderList(trials) {
    if (!list) return;
    list.replaceChildren();
    trials.forEach(function (trial, index) {
      var item = document.createElement("li");
      item.appendChild(el("span", "", trial.sku + " " + trial.week + " " + fmt(trial.cases)));
      var button = el("button", "", "Remove");
      button.type = "button";
      button.setAttribute("aria-label", "Remove " + trial.sku + " " + trial.week);
      button.addEventListener("click", function () {
        commit(readTrials().filter(function (_, itemIndex) { return itemIndex !== index; }));
      });
      item.appendChild(button);
      list.appendChild(item);
    });
  }

  function commit(trials) {
    var previous = readTrials();
    writeTrials(trials);
    renderList(trials);
    showError("");
    return fetch("/board", {
      method: "POST",
      headers: { "Content-Type": "application/json", Accept: "application/json" },
      body: JSON.stringify({ trials: trials }),
    }).then(function (res) {
      return res.json().then(function (data) {
        if (!res.ok) throw new Error((data && data.error) || "Trial run failed");
        return data;
      });
    }).then(paintBoard).catch(function (err) {
      writeTrials(previous);
      renderList(previous);
      showError(err.message || "Trial run failed");
    });
  }

  function downloadPlan(event) {
    event.preventDefault();
    showError("");
    fetch("/session-plan.xlsx", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ trials: readTrials() }),
    }).then(function (res) {
      if (!res.ok) {
        return res.json().then(function (data) {
          throw new Error((data && data.error) || "Could not download the session plan");
        });
      }
      return res.blob();
    }).then(function (blob) {
      var url = URL.createObjectURL(blob);
      var link = document.createElement("a");
      link.href = url;
      link.download = "session-plan.xlsx";
      document.body.appendChild(link);
      link.click();
      link.remove();
      URL.revokeObjectURL(url);
    }).catch(function (err) {
      showError(err.message || "Could not download the session plan");
    });
  }

  if (form) {
    fillSelect(form.elements.sku, readJsonAttr("data-master"));
    fillSelect(form.elements.week, readJsonAttr("data-weeks"));
    form.addEventListener("submit", function (event) {
      event.preventDefault();
      var casesInput = form.elements.cases;
      var qty = Number(casesInput.value);
      if (casesInput.value === "" || !Number.isFinite(qty)) return;
      var trials = readTrials();
      trials.push({
        sku: form.elements.sku.value,
        week: form.elements.week.value,
        cases: qty,
      });
      casesInput.value = "";
      commit(trials);
    });
  }

  var plan = document.querySelector("a.plan");
  if (plan) plan.addEventListener("click", downloadPlan);

  var stored = readTrials();
  if (stored.length) commit(stored);
  else renderList(stored);
})();
