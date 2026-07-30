class CallMonitorTestCard extends HTMLElement {
  constructor() {
    super();
    this._activeFilter = "all";
    this._boundClickHandler = this._handleClick.bind(this);
  }

  connectedCallback() {
    this.addEventListener("click", this._boundClickHandler);
  }

  disconnectedCallback() {
    this.removeEventListener("click", this._boundClickHandler);
  }

  setConfig(config) {
    if (!config.entity) {
      throw new Error("Bitte eine entity angeben.");
    }

    this.config = {
      title: "Eingehende Anrufe",
      max_calls: 10,
      show_called_number: false,
      ...config,
    };

    this._render();
  }

  set hass(hass) {
    this._hass = hass;
    this._render();
  }

  getCardSize() {
    const count = Number(this.config?.max_calls || 10);
    return Math.max(2, Math.ceil(count / 2));
  }

  _handleClick(event) {
    const button = event.target.closest("[data-filter]");
    if (!button || !this.contains(button)) return;

    event.preventDefault();
    event.stopPropagation();

    const filter = button.dataset.filter;
    if (!filter || filter === this._activeFilter) return;

    this._activeFilter = filter;
    this._render();
  }

  _filterCalls(calls) {
    if (this._activeFilter === "missed") {
      return calls.filter((call) => call.status === "missed");
    }

    if (this._activeFilter === "answering_machine") {
      return calls.filter((call) => call.status === "answering_machine");
    }

    return calls;
  }

  _appearance(status) {
    const styles = {
      answered: {
        icon: "mdi:phone-outline",
        color: "var(--success-color, #43a047)",
        label: "Anruf angenommen",
      },
      missed: {
        icon: "mdi:phone-missed-outline",
        color: "var(--error-color, #db4437)",
        label: "Verpasster Anruf",
      },
      answering_machine: {
        icon: "mdi:file-phone-outline",
        color: "var(--info-color, #2196f3)",
        label: "Vom Anrufbeantworter angenommen",
      },
    };

    return styles[status] || {
      icon: "mdi:phone-outline",
      color: "var(--secondary-text-color)",
      label: "Eingehender Anruf",
    };
  }

  _formatDuration(value) {
    const seconds = Number(value);

    if (!Number.isFinite(seconds) || seconds < 0) {
      return "";
    }

    if (seconds < 60) {
      return `${Math.floor(seconds)} Sek.`;
    }

    if (seconds < 3600) {
      return `${Math.floor(seconds / 60)} Min.`;
    }

    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    return `${hours} Std. ${minutes} Min.`;
  }

  _formatDate(value) {
    if (!value) return "";

    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return value;

    const now = new Date();
    const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
    const callDay = new Date(
      date.getFullYear(),
      date.getMonth(),
      date.getDate()
    );
    const diffDays = Math.round((today - callDay) / 86400000);

    const time = new Intl.DateTimeFormat("de-DE", {
      hour: "2-digit",
      minute: "2-digit",
    }).format(date);

    if (diffDays === 0) return `Heute um ${time}`;
    if (diffDays === 1) return `Gestern um ${time}`;

    return new Intl.DateTimeFormat("de-DE", {
      day: "2-digit",
      month: "2-digit",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    }).format(date);
  }

  _escape(value) {
    return String(value ?? "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#039;");
  }

  _render() {
    if (!this._hass || !this.config) return;

    const stateObj = this._hass.states[this.config.entity];
    const calls = Array.isArray(stateObj?.attributes?.calls)
      ? stateObj.attributes.calls
      : [];

    const maxCalls = Math.max(1, Number(this.config.max_calls || 10));
    const visibleCalls = this._filterCalls(calls).slice(0, maxCalls);

    const filters = [
      { id: "all", label: "Alle" },
      { id: "missed", label: "Verpasst" },
      { id: "answering_machine", label: "Anrufbeantworter" },
    ];

    const filterButtons = filters
      .map(
        (filter) => `
          <button
            class="filter-chip ${
              this._activeFilter === filter.id ? "active" : ""
            }"
            data-filter="${filter.id}"
            type="button"
            aria-pressed="${
              this._activeFilter === filter.id ? "true" : "false"
            }"
          >
            ${filter.label}
          </button>
        `
      )
      .join("");

    const rows = visibleCalls
      .map((call) => {
        const appearance = this._appearance(call.status);
        const caller = call.caller || "unterdrückte Rufnummer";
        const duration =
          call.status !== "missed" && call.duration_seconds != null
            ? ` · ${this._escape(
                this._formatDuration(call.duration_seconds)
              )}`
            : "";

        const calledNumber =
          this.config.show_called_number && call.called
            ? `<div class="called">Angerufene Nummer: ${this._escape(
                call.called
              )}</div>`
            : "";

        return `
          <div class="call-row">
            <div class="icon-badge" style="--call-color:${appearance.color}">
              <ha-icon icon="${appearance.icon}"></ha-icon>
            </div>

            <div class="call-main">
              <div class="caller">${this._escape(caller)}</div>
              <div class="meta">
                <span>${this._escape(this._formatDate(call.timestamp))}</span>
              </div>
              <div class="status">
                ${appearance.label}${duration}
              </div>
              ${calledNumber}
            </div>
          </div>
        `;
      })
      .join("");

    this.innerHTML = `
      <ha-card>
        <div class="header-row">
          <div class="title">${this._escape(this.config.title)}</div>
          <div class="filters" role="group" aria-label="Anruffilter">
            ${filterButtons}
          </div>
        </div>

        <div class="card-content">
          ${
            rows ||
            '<div class="empty">Keine passenden Anrufe vorhanden.</div>'
          }
        </div>
      </ha-card>

      <style>
        ha-card {
          overflow: hidden;
        }

        .header-row {
          display: flex;
          align-items: center;
          justify-content: space-between;
          gap: 12px;
          padding: 16px 16px 10px;
          flex-wrap: wrap;
        }

        .title {
          font-size: 1.2rem;
          font-weight: 500;
          color: var(--primary-text-color);
        }

        .filters {
          display: inline-flex;
          align-items: center;
          gap: 4px;
          padding: 3px;
          border-radius: 999px;
          background: var(--secondary-background-color);
        }

        .filter-chip {
          appearance: none;
          border: 0;
          border-radius: 999px;
          background: transparent;
          color: var(--secondary-text-color);
          font: inherit;
          font-size: 0.82rem;
          font-weight: 500;
          line-height: 1;
          padding: 8px 12px;
          cursor: pointer;
          transition:
            background-color 120ms ease,
            color 120ms ease,
            box-shadow 120ms ease;
          white-space: nowrap;
        }

        .filter-chip:hover {
          color: var(--primary-text-color);
          background: rgba(var(--rgb-primary-text-color, 0, 0, 0), 0.06);
        }

        .filter-chip.active {
          color: var(--primary-color);
          background: var(--card-background-color);
          box-shadow: 0 1px 3px rgba(0, 0, 0, 0.18);
        }

        .card-content {
          padding: 0 16px 8px;
        }

        .call-row {
          display: grid;
          grid-template-columns: 42px minmax(0, 1fr);
          gap: 12px;
          align-items: start;
          padding: 13px 0;
          border-bottom: 1px solid var(--divider-color);
        }

        .call-row:last-child {
          border-bottom: 0;
        }

        .icon-badge {
          width: 38px;
          height: 38px;
          border-radius: 50%;
          display: flex;
          align-items: center;
          justify-content: center;
          color: var(--call-color);
          background: color-mix(
            in srgb,
            var(--call-color) 12%,
            transparent
          );
        }

        .icon-badge ha-icon {
          --mdc-icon-size: 23px;
        }

        .call-main {
          min-width: 0;
        }

        .caller {
          color: var(--primary-text-color);
          font-weight: 500;
          font-size: 1rem;
          overflow: hidden;
          text-overflow: ellipsis;
          white-space: nowrap;
        }

        .meta,
        .status,
        .called,
        .empty {
          color: var(--secondary-text-color);
          font-size: 0.88rem;
        }

        .meta {
          margin-top: 2px;
        }

        .status {
          margin-top: 5px;
          color: var(--primary-text-color);
        }

        .called {
          margin-top: 3px;
        }

        .empty {
          padding: 16px 0 20px;
        }

        @media (max-width: 600px) {
          .header-row {
            align-items: flex-start;
          }

          .filters {
            width: 100%;
            overflow-x: auto;
            justify-content: flex-start;
          }

          .filter-chip {
            flex: 0 0 auto;
          }
        }
      </style>
    `;
  }
}

if (!customElements.get("callmonitor-test-card")) {
  customElements.define("callmonitor-test-card", CallMonitorTestCard);
}

window.customCards = window.customCards || [];
window.customCards.push({
  type: "callmonitor-test-card",
  name: "CallMonitor-Test Card",
  description: "Zeigt eingehende FRITZ!Box-Anrufe mit Filtern an.",
  preview: false,
});
