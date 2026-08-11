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
    const playButton = event.target.closest("[data-action='play-voicemail']");
    if (playButton && this.contains(playButton)) {
      event.preventDefault();
      event.stopPropagation();
      this._playVoicemail(playButton.dataset.mediaSource || "");
      return;
    }

    const menuButton = event.target.closest("[data-action='toggle-menu']");
    if (menuButton && this.contains(menuButton)) {
      event.preventDefault();
      event.stopPropagation();
      const callId = menuButton.dataset.callId || "";
      this._openMenuCallId =
        this._openMenuCallId === callId ? null : callId;
      this._render();
      return;
    }

    const deleteButton = event.target.closest("[data-action='delete-call']");
    if (deleteButton && this.contains(deleteButton)) {
      event.preventDefault();
      event.stopPropagation();
      this._deleteCall(deleteButton.dataset.callId || "");
      return;
    }

    const addButton = event.target.closest("[data-action='add-contact']");
    if (addButton && this.contains(addButton)) {
      event.preventDefault();
      event.stopPropagation();
      this._contactDraft = {
        number: addButton.dataset.number || "",
      };
      this._contactError = "";
      this._render();
      return;
    }

    const cancelButton = event.target.closest("[data-action='cancel-contact']");
    if (cancelButton && this.contains(cancelButton)) {
      event.preventDefault();
      this._contactDraft = null;
      this._contactError = "";
      this._render();
      return;
    }

    const saveButton = event.target.closest("[data-action='save-contact']");
    if (saveButton && this.contains(saveButton)) {
      event.preventDefault();
      this._saveContact();
      return;
    }

    const clearButton = event.target.closest("[data-action='clear']");
    if (clearButton && this.contains(clearButton)) {
      event.preventDefault();
      event.stopPropagation();
      this._clearCalls();
      return;
    }

    const button = event.target.closest("[data-filter]");
    if (!button || !this.contains(button)) return;

    event.preventDefault();
    event.stopPropagation();

    const filter = button.dataset.filter;
    if (!filter || filter === this._activeFilter) return;

    this._activeFilter = filter;
    this._render();
  }

  async _playVoicemail(mediaSourceId) {
    if (!this._hass || !mediaSourceId) return;

    this._voicemailPlayError = "";
    this._voicemailLoading = mediaSourceId;
    this._render();

    try {
      const resolvedMedia = await this._hass.callWS({
        type: "media_source/resolve_media",
        media_content_id: mediaSourceId,
      });

      if (!resolvedMedia?.url) {
        throw new Error("Media Source hat keine URL geliefert.");
      }

      const signed = await this._hass.callWS({
        type: "auth/sign_path",
        path: resolvedMedia.url,
        expires: 60,
      });

      if (!signed?.path) {
        throw new Error("Home Assistant konnte den Audiopfad nicht signieren.");
      }

      if (this._voicemailAudio) {
        this._voicemailAudio.pause();
        this._voicemailAudio.src = "";
        this._voicemailAudio = null;
      }

      const audioUrl = window.location.origin + signed.path;
      const audio = new Audio();
      audio.preload = "metadata";
      audio.src = audioUrl;
      audio.type = resolvedMedia.mime_type || "audio/wav";

      audio.onerror = () => {
        const code = audio.error?.code;
        const message = audio.error?.message || "Unbekannter Audiofehler";
        this._voicemailPlayError =
          `Audio konnte nicht geladen werden (Code ${code || "?"}: ${message}).`;
        this._voicemailLoading = "";
        this._render();
        console.error("FritzCallMonitor audio error:", audio.error, audioUrl);
      };

      audio.oncanplay = () => {
        this._voicemailLoading = "";
        this._render();
      };

      this._voicemailAudio = audio;
      await audio.play();
    } catch (error) {
      this._voicemailLoading = "";
      this._voicemailPlayError =
        error?.message || String(error) || "Wiedergabe fehlgeschlagen.";
      this._render();
      console.error("FritzCallMonitor: Audio engine failed:", error);
    }
  }

  async _deleteCall(callId) {
    if (!this._hass || !callId) return;

    this._openMenuCallId = null;

    try {
      await this._hass.callService("callmonitor_test", "delete_call", {
        call_id: callId,
      });
    } catch (error) {
      console.error(
        "FritzCallMonitor: Anruf konnte nicht gelöscht werden.",
        error
      );
    }
  }

  async _saveContact() {
    const nameInput = this.querySelector("#fcm-contact-name");
    const phonebookSelect = this.querySelector("#fcm-phonebook");
    if (!nameInput || !phonebookSelect || !this._contactDraft) return;

    const name = nameInput.value.trim();
    const phonebookId = Number(phonebookSelect.value);

    if (!name) {
      this._contactError = "Bitte einen Namen eingeben.";
      this._render();
      return;
    }

    this._contactSaving = true;
    this._contactError = "";
    this._render();

    try {
      await this._hass.callService("callmonitor_test", "add_contact", {
        name,
        number: this._contactDraft.number,
        phonebook_id: phonebookId,
      });
      this._contactDraft = null;
      this._contactSaving = false;
      this._contactError = "";
    } catch (error) {
      console.error("FritzCallMonitor: Kontakt konnte nicht angelegt werden.", error);
      this._contactSaving = false;
      this._contactError = "Kontakt konnte nicht gespeichert werden.";
    }

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

    const phonebooks = Array.isArray(stateObj?.attributes?.telefonbuch_liste)
      ? stateObj.attributes.telefonbuch_liste
      : [];

    const voicemailEntity =
      this.config.voicemail_entity ||
      "sensor.fritzcallmonitor_anrufbeantworter";
    const voicemailState = this._hass.states[voicemailEntity];
    const voicemails = Array.isArray(voicemailState?.attributes?.nachrichten)
      ? voicemailState.attributes.nachrichten
      : [];

    const rows = visibleCalls
      .map((call) => {
        const appearance = this._appearance(call.status);
        const caller = call.caller || "unterdrückte Rufnummer";
        const callerName = call.caller_name || "";
        const duration =
          call.status !== "missed" && call.duration_seconds != null
            ? ` · ${this._escape(
                this._formatDuration(call.duration_seconds)
              )}`
            : "";

        const dateText = this._escape(this._formatDate(call.timestamp));
        const secondLine = callerName
          ? `${this._escape(caller)} · ${dateText} · ${appearance.label}${duration}`
          : `${dateText} · ${appearance.label}${duration}`;

        const canAddContact =
          !callerName &&
          caller &&
          caller !== "unterdrückte Rufnummer" &&
          phonebooks.length > 0;

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
              <div class="caller">${this._escape(
                callerName || caller
              )}</div>
              <div class="call-details">${secondLine}</div>
              ${calledNumber}
            </div>

            <div class="row-menu-wrap">
              <button
                class="row-action"
                data-action="toggle-menu"
                data-call-id="${this._escape(call.call_id || "")}"
                type="button"
                title="Weitere Aktionen"
                aria-label="Weitere Aktionen"
              >
                <ha-icon icon="mdi:dots-vertical"></ha-icon>
              </button>

              ${
                this._openMenuCallId === call.call_id
                  ? `
                    <div class="row-menu">
                      ${
                        canAddContact
                          ? `
                            <button
                              class="menu-item"
                              data-action="add-contact"
                              data-number="${this._escape(caller)}"
                              type="button"
                            >
                              <ha-icon icon="mdi:account-plus-outline"></ha-icon>
                              <span>Kontakt hinzufügen</span>
                            </button>
                          `
                          : ""
                      }

                      <button
                        class="menu-item danger"
                        data-action="delete-call"
                        data-call-id="${this._escape(call.call_id || "")}"
                        type="button"
                      >
                        <ha-icon icon="mdi:delete-outline"></ha-icon>
                        <span>Löschen</span>
                      </button>
                    </div>
                  `
                  : ""
              }
            </div>
          </div>
        `;
      })
      .join("");

    const voicemailRows = voicemails
      .slice(0, maxCalls)
      .map((message) => {
        const caller =
          message.caller_name ||
          message.name ||
          message.caller ||
          "Unbekannter Anrufer";
        const seconds = Number(message.duration_seconds);
        let formattedDuration = "";
        if (Number.isFinite(seconds) && seconds > 0) {
          if (seconds < 60) {
            formattedDuration = `${Math.round(seconds)} Sek.`;
          } else {
            const minutes = Math.floor(seconds / 60);
            const rest = Math.round(seconds % 60);
            formattedDuration = rest
              ? `${minutes} Min. ${rest} Sek.`
              : `${minutes} Min.`;
          }
        } else {
          formattedDuration = String(message.duration || "");
        }
        const duration = formattedDuration
          ? ` · ${this._escape(formattedDuration)}`
          : "";
        const newLabel = message.new ? " · Neu" : "";
        const loading =
          this._voicemailLoading === message.media_source_id;

        return `
          <div class="call-row voicemail-row">
            <div class="icon-badge" style="--call-color:var(--info-color, #2196f3)">
              <ha-icon icon="mdi:voicemail"></ha-icon>
            </div>

            <div class="call-main">
              <div class="caller">${this._escape(caller)}</div>
              <div class="call-details">
                ${this._escape(message.date || "")}${duration}${newLabel}
              </div>
            </div>

            <button
              class="row-action"
              data-action="play-voicemail"
              data-media-source="${this._escape(message.media_source_id || "")}"
              type="button"
              title="Nachricht abspielen"
              aria-label="Nachricht abspielen"
              ${loading ? "disabled" : ""}
            >
              <ha-icon icon="${loading ? "mdi:loading" : "mdi:play-circle-outline"}"></ha-icon>
            </button>
          </div>
        `;
      })
      .join("");

    const voicemailPlayer =
      false
        ? `
          <div class="voicemail-player">
            <audio
              controls
              autoplay
              src="${this._escape(this._voicemailAudio.url)}"
            ></audio>
          </div>
        `
        : "";

    const voicemailError =
      this._voicemailPlayError
        ? `<div class="empty voicemail-error">${this._escape(this._voicemailPlayError)}</div>`
        : "";

    const phonebookOptions = phonebooks
      .map(
        (book) =>
          `<option value="${Number(book.id)}">${this._escape(book.name)}</option>`
      )
      .join("");

    const contactDialog = this._contactDraft
      ? `
        <div class="modal-backdrop">
          <div class="contact-dialog" role="dialog" aria-modal="true">
            <div class="dialog-title">Kontakt hinzufügen</div>
            <div class="dialog-number">${this._escape(
              this._contactDraft.number
            )}</div>

            <label class="field-label" for="fcm-contact-name">Name</label>
            <input
              id="fcm-contact-name"
              class="dialog-input"
              type="text"
              autocomplete="name"
              placeholder="Max Mustermann"
              ${this._contactSaving ? "disabled" : ""}
            />

            <label class="field-label" for="fcm-phonebook">Telefonbuch</label>
            <select
              id="fcm-phonebook"
              class="dialog-input"
              ${this._contactSaving ? "disabled" : ""}
            >
              ${phonebookOptions}
            </select>

            ${
              this._contactError
                ? `<div class="dialog-error">${this._escape(
                    this._contactError
                  )}</div>`
                : ""
            }

            <div class="dialog-actions">
              <button
                class="dialog-button"
                data-action="cancel-contact"
                type="button"
                ${this._contactSaving ? "disabled" : ""}
              >
                Abbrechen
              </button>
              <button
                class="dialog-button primary"
                data-action="save-contact"
                type="button"
                ${this._contactSaving ? "disabled" : ""}
              >
                ${this._contactSaving ? "Speichere…" : "Speichern"}
              </button>
            </div>
          </div>
        </div>
      `
      : "";

    this.innerHTML = `
      <ha-card>
        <div class="header-row">
          <div class="title">${this._escape(this.config.title)}</div>
          <div class="actions">
            <div class="filters" role="group" aria-label="Anruffilter">
              ${filterButtons}
            </div>
            <button
              class="clear-button"
              data-action="clear"
              type="button"
              title="Anrufliste löschen"
              aria-label="Anrufliste löschen"
            >
              <span>Clear all</span>
              <ha-icon icon="mdi:delete-outline"></ha-icon>
            </button>
          </div>
        </div>

        <div class="card-content">
          ${
            this._activeFilter === "answering_machine"
              ? (
                  `${voicemailRows}${rows}` ||
                  '<div class="empty">Keine Anrufe oder AB-Nachrichten vorhanden.</div>'
                )
              : (
                  rows ||
                  '<div class="empty">Keine passenden Anrufe vorhanden.</div>'
                )
          }
          ${voicemailError}
        </div>
      </ha-card>
      ${contactDialog}

      <style>
        ha-card {
          overflow: visible;
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

        .actions {
          display: flex;
          align-items: center;
          gap: 8px;
          min-width: 0;
          flex: 1 1 auto;
        }

        .filters {
          display: inline-flex;
          align-items: center;
          justify-content: flex-start;
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

        .clear-button {
          appearance: none;
          margin-left: auto;
          min-height: 36px;
          flex: 0 0 auto;
          display: inline-flex;
          align-items: center;
          justify-content: center;
          gap: 6px;
          border: 0;
          border-radius: 999px;
          padding: 0 10px 0 12px;
          background: transparent;
          color: var(--error-color, #db4437);
          font: inherit;
          font-size: 0.82rem;
          font-weight: 500;
          cursor: pointer;
          transition:
            background-color 120ms ease,
            transform 120ms ease;
        }

        .clear-button:hover {
          background: color-mix(
            in srgb,
            var(--error-color, #db4437) 12%,
            transparent
          );
        }

        .clear-button:active {
          transform: scale(0.94);
        }

        .clear-button ha-icon {
          --mdc-icon-size: 22px;
        }

        .card-content {
          overflow: visible;
          padding: 0 16px 8px;
        }

        .call-row {
          display: grid;
          grid-template-columns: 42px minmax(0, 1fr) auto;
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

        .call-details,
        .called,
        .empty {
          color: var(--secondary-text-color);
          font-size: 0.88rem;
        }

        .called {
          margin-top: 3px;
        }


        .call-details {
          margin-top: 3px;
          line-height: 1.35;
        }

        .row-action {
          appearance: none;
          border: 0;
          background: transparent;
          color: var(--primary-color);
          width: 34px;
          height: 34px;
          border-radius: 50%;
          display: flex;
          align-items: center;
          justify-content: center;
          cursor: pointer;
          align-self: center;
        }

        .row-action:hover {
          background: var(--secondary-background-color);
        }

        .row-action ha-icon {
          --mdc-icon-size: 21px;
        }

        .voicemail-player {
          padding: 10px 0 14px;
        }

        .voicemail-player audio {
          width: 100%;
        }

        .voicemail-row .row-action[disabled] ha-icon {
          animation: fcm-spin 1s linear infinite;
        }

        @keyframes fcm-spin {
          from { transform: rotate(0deg); }
          to { transform: rotate(360deg); }
        }

        .row-menu-wrap {
          position: relative;
          align-self: center;
        }

        .row-menu {
          position: absolute;
          right: 0;
          bottom: 38px;
          z-index: 50;
          min-width: 190px;
          padding: 6px;
          border: 1px solid var(--divider-color);
          border-radius: 12px;
          background: var(--card-background-color);
          box-shadow: 0 8px 28px rgba(0, 0, 0, 0.24);
        }

        .menu-item {
          appearance: none;
          width: 100%;
          display: flex;
          align-items: center;
          gap: 10px;
          border: 0;
          border-radius: 8px;
          padding: 10px 11px;
          background: transparent;
          color: var(--primary-text-color);
          font: inherit;
          font-size: 0.9rem;
          text-align: left;
          cursor: pointer;
        }

        .menu-item:hover {
          background: var(--secondary-background-color);
        }

        .menu-item.danger {
          color: var(--error-color, #db4437);
        }

        .menu-item ha-icon {
          --mdc-icon-size: 20px;
        }

        .modal-backdrop {
          position: fixed;
          inset: 0;
          z-index: 1000;
          display: flex;
          align-items: center;
          justify-content: center;
          padding: 20px;
          background: rgba(0, 0, 0, 0.45);
        }

        .contact-dialog {
          width: min(420px, calc(100vw - 40px));
          background: var(--card-background-color);
          color: var(--primary-text-color);
          border-radius: 16px;
          padding: 20px;
          box-shadow: 0 12px 40px rgba(0, 0, 0, 0.35);
        }

        .dialog-title {
          font-size: 1.2rem;
          font-weight: 600;
        }

        .dialog-number {
          color: var(--secondary-text-color);
          margin: 4px 0 18px;
        }

        .field-label {
          display: block;
          font-size: 0.85rem;
          color: var(--secondary-text-color);
          margin: 12px 0 5px;
        }

        .dialog-input {
          box-sizing: border-box;
          width: 100%;
          min-height: 42px;
          border: 1px solid var(--divider-color);
          border-radius: 8px;
          padding: 8px 10px;
          background: var(--primary-background-color);
          color: var(--primary-text-color);
          font: inherit;
        }

        .dialog-error {
          margin-top: 12px;
          color: var(--error-color, #db4437);
          font-size: 0.88rem;
        }

        .dialog-actions {
          display: flex;
          justify-content: flex-end;
          gap: 8px;
          margin-top: 20px;
        }

        .dialog-button {
          appearance: none;
          border: 0;
          border-radius: 999px;
          padding: 9px 15px;
          background: var(--secondary-background-color);
          color: var(--primary-text-color);
          font: inherit;
          font-weight: 500;
          cursor: pointer;
        }

        .dialog-button.primary {
          background: var(--primary-color);
          color: var(--text-primary-color, #fff);
        }

        .dialog-button:disabled {
          opacity: 0.55;
          cursor: default;
        }

        .empty {
          padding: 16px 0 20px;
        }

        @media (max-width: 600px) {
          .header-row {
            align-items: flex-start;
          }

          .actions {
            width: 100%;
            display: flex;
            align-items: center;
          }

          .filters {
            min-width: 0;
            flex: 0 1 auto;
            overflow-x: auto;
            justify-content: flex-start;
          }

          .clear-button {
            margin-left: auto;
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
  name: "FritzCallMonitor Card",
  description: "Zeigt eingehende FRITZ!Box-Anrufe mit Filtern an.",
  preview: false,
});
