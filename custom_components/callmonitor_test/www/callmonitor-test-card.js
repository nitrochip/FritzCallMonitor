class CallMonitorTestCard extends HTMLElement {
  setConfig(config) {
    if (!config.entity) throw new Error("Bitte eine entity angeben.");
    this.config = {
      title: "Eingehende Anrufe",
      max_calls: 10,
      show_called_number: false,
      ...config,
    };
  }

  set hass(hass) {
    this._hass = hass;
    this._render();
  }

  getCardSize() {
    return Math.max(2, Math.ceil(Number(this.config?.max_calls || 10) / 2));
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
    const callDay = new Date(date.getFullYear(), date.getMonth(), date.getDate());
    const diffDays = Math.round((today - callDay) / 86400000);
    const time = new Intl.DateTimeFormat("de-DE", {
      hour: "2-digit",
      minute: "2-digit",
    }).format(date);
    if (diffDays === 0) return `Heute, ${time}`;
    if (diffDays === 1) return `Gestern, ${time}`;
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
    const visibleCalls = calls.slice(0, Math.max(1, Number(this.config.max_calls || 10)));
    const rows = visibleCalls.map((call) => {
      const appearance = this._appearance(call.status);
      const caller = call.caller || "unterdrückte Rufnummer";
      const called = this.config.show_called_number && call.called
        ? `<div class="called">Angerufene Nummer: ${this._escape(call.called)}</div>`
        : "";
      return `
        <div class="call-row">
          <div class="icon-wrap" style="color:${appearance.color}">
            <ha-icon icon="${appearance.icon}"></ha-icon>
          </div>
          <div class="call-content">
            <div class="caller">${this._escape(caller)}</div>
            <div class="status">${appearance.label}</div>
            ${called}
          </div>
          <div class="time">${this._escape(this._formatDate(call.timestamp))}</div>
        </div>`;
    }).join("");

    this.innerHTML = `
      <ha-card>
        <div class="card-header">${this._escape(this.config.title)}</div>
        <div class="card-content">
          ${rows || '<div class="empty">Noch keine eingehenden Anrufe gespeichert.</div>'}
        </div>
      </ha-card>
      <style>
        .card-content { padding-top: 0; }
        .call-row {
          display: grid;
          grid-template-columns: 42px minmax(0, 1fr) auto;
          gap: 10px;
          align-items: center;
          padding: 12px 0;
          border-bottom: 1px solid var(--divider-color);
        }
        .call-row:last-child { border-bottom: 0; }
        .icon-wrap { display: flex; align-items: center; justify-content: center; }
        .icon-wrap ha-icon { --mdc-icon-size: 28px; }
        .call-content { min-width: 0; }
        .caller {
          font-weight: 500;
          overflow: hidden;
          text-overflow: ellipsis;
          white-space: nowrap;
        }
        .status, .called, .time, .empty {
          color: var(--secondary-text-color);
          font-size: 0.9rem;
        }
        .called { margin-top: 2px; }
        .time { white-space: nowrap; align-self: start; padding-top: 2px; text-align: right; }
        @media (max-width: 520px) {
          .call-row { grid-template-columns: 38px minmax(0, 1fr); }
          .time { grid-column: 2; text-align: left; padding-top: 0; }
        }
      </style>`;
  }
}

customElements.define("callmonitor-test-card", CallMonitorTestCard);
window.customCards = window.customCards || [];
window.customCards.push({
  type: "callmonitor-test-card",
  name: "CallMonitor-Test Card",
  description: "Zeigt eingehende FRITZ!Box-Anrufe an.",
  preview: false,
});
