const $ = (id) => document.getElementById(id);
const state = { rooms: [], reservations: [] };

async function api(path, options) {
  const res = await fetch("/api" + path, options);
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.error || `Request failed (${res.status})`);
  return data;
}

function jsonOptions(method, body) {
  return {
    method,
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  };
}

// ---------- feedback ----------

let toastTimer;
function toast(message, kind = "ok") {
  const el = $("toast");
  el.textContent = message;
  el.className = kind;
  el.hidden = false;
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => (el.hidden = true), 4000);
}

// ---------- theme ----------

// No stored choice means "whatever the OS says", so the label is derived, not stored.
const themeToggle = $("theme-toggle");
const isDark = () =>
  (localStorage.theme || (matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light")) === "dark";
const labelTheme = () => (themeToggle.textContent = isDark() ? "☀ Light mode" : "🌙 Dark mode");

themeToggle.onclick = () => {
  document.documentElement.style.colorScheme = localStorage.theme = isDark() ? "light" : "dark";
  labelTheme();
};
matchMedia("(prefers-color-scheme: dark)").addEventListener("change", labelTheme);
labelTheme();

/** Render one field's native constraint result into its inline error slot. */
function showFieldError(el) {
  const ok = el.checkValidity();
  const slot = $(el.id + "-error");
  if (!slot) return ok;
  let message = "";
  if (!ok) {
    if (el.validity.valueMissing) message = "This field is required.";
    else if (el.validity.customError) message = el.validationMessage;
    else message = el.dataset.hint || el.validationMessage;
  }
  slot.textContent = message;
  el.classList.toggle("invalid", !ok);
  el.setAttribute("aria-invalid", ok ? "false" : "true");
  return ok;
}

function showErrors(form, focus = false) {
  let firstBad = null;
  for (const el of form.elements) {
    if (!showFieldError(el) && !firstBad) firstBad = el;
  }
  if (focus && firstBad) firstBad.focus();
  return !firstBad;
}

/** A reset form is not a wrong form: wipe the messages instead of re-running them. */
function clearErrors(form) {
  for (const el of form.elements) {
    const slot = $(el.id + "-error");
    if (!slot) continue;
    slot.textContent = "";
    el.classList.remove("invalid");
    el.setAttribute("aria-invalid", "false");
  }
}

// Flag a field once the user leaves it, then keep it live until it is fixed —
// never re-check the whole form mid-typing, that moves focus out from under them.
for (const form of [$("room-form"), $("res-form")]) {
  form.addEventListener("focusout", (e) => {
    if (e.target.value || e.target.getAttribute("aria-invalid") === "true") {
      showFieldError(e.target);
    }
  });
  form.addEventListener("input", (e) => {
    if (e.target.getAttribute("aria-invalid") === "true") showFieldError(e.target);
  });
}

/** Disable a form while its request is in flight so nothing double-submits. */
async function submitting(button, work) {
  const label = button.textContent;
  button.disabled = true;
  button.textContent = "Saving…";
  try {
    await work();
  } catch (err) {
    toast(err.message, "error");
  } finally {
    button.disabled = false;
    button.textContent = label;
  }
}

// ---------- formatting ----------

const money = new Intl.NumberFormat(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
const today = () => new Date().toISOString().slice(0, 10);
const nightsBetween = (checkIn, checkOut) =>
  Math.round((Date.parse(checkOut) - Date.parse(checkIn)) / 86400000);

function fmtDate(iso) {
  const [y, m, d] = iso.split("-").map(Number);
  return new Date(y, m - 1, d).toLocaleDateString(undefined, {
    day: "numeric", month: "short", year: "numeric",
  });
}

function emptyRow(tbody, columns, message) {
  const tr = tbody.insertRow();
  const td = tr.insertCell();
  td.colSpan = columns;
  td.className = "empty";
  td.textContent = message;
}

// ---------- rooms ----------

const roomForm = $("room-form");
const roomId = $("room-id");
const roomNumber = $("room-number");
const roomType = $("room-type");
const roomPrice = $("room-price");
const roomSave = $("room-save");
const roomCancel = $("room-cancel");
const roomsBody = $("rooms-body");
const resRoomSelect = $("res-room");

function renderRooms() {
  roomsBody.innerHTML = "";
  const selected = resRoomSelect.value;
  resRoomSelect.innerHTML = '<option value="">Select a room</option>';

  if (!state.rooms.length) {
    emptyRow(roomsBody, 5, "No rooms yet. Add one above to start taking bookings.");
    return;
  }

  const now = today();
  for (const room of state.rooms) {
    const stay = state.reservations.find(
      (r) => r.room_id === room.id && r.check_in <= now && r.check_out > now
    );
    const tr = roomsBody.insertRow();
    tr.insertCell().textContent = room.room_number;
    tr.insertCell().textContent = room.room_type;
    tr.insertCell().textContent = money.format(room.price);

    const status = tr.insertCell();
    const badge = document.createElement("span");
    badge.className = stay ? "badge occupied" : "badge free";
    badge.textContent = stay ? `Occupied · ${stay.guest_name}` : "Available";
    status.appendChild(badge);

    const actions = tr.insertCell();
    actions.className = "row-actions";
    actions.append(
      button("Edit", () => editRoom(room)),
      button("Delete", () => deleteRoom(room), "danger")
    );

    const opt = new Option(
      `${room.room_number} — ${room.room_type} (${money.format(room.price)}/night)`,
      room.id
    );
    resRoomSelect.appendChild(opt);
  }
  resRoomSelect.value = selected;
}

function button(text, onclick, className = "secondary") {
  const el = document.createElement("button");
  el.type = "button";
  el.className = className;
  el.textContent = text;
  el.onclick = onclick;
  return el;
}

function editRoom(room) {
  roomId.value = room.id;
  roomNumber.value = room.room_number;
  roomType.value = room.room_type;
  roomPrice.value = room.price;
  roomSave.textContent = "Update room";
  roomCancel.hidden = false;
  roomNumber.focus();
}

async function deleteRoom(room) {
  if (!confirm(`Delete room ${room.room_number}? This cannot be undone.`)) return;
  try {
    await api(`/rooms/${room.id}`, { method: "DELETE" });
    toast(`Room ${room.room_number} deleted.`);
    if (roomId.value === String(room.id)) resetRoomForm();
    refresh();
  } catch (err) {
    toast(err.message, "error");
  }
}

function resetRoomForm() {
  roomForm.reset();
  roomId.value = "";
  roomSave.textContent = "Add room";
  roomCancel.hidden = true;
  clearErrors(roomForm);
}

roomForm.onsubmit = (e) => {
  e.preventDefault();
  if (!showErrors(roomForm, true)) return;
  const id = roomId.value;
  const body = {
    room_number: roomNumber.value.trim(),
    room_type: roomType.value,
    price: parseFloat(roomPrice.value),
  };
  submitting(roomSave, async () => {
    await api(id ? `/rooms/${id}` : "/rooms", jsonOptions(id ? "PUT" : "POST", body));
    toast(id ? `Room ${body.room_number} updated.` : `Room ${body.room_number} added.`);
    resetRoomForm();
    await refresh();
  });
};

roomCancel.onclick = resetRoomForm;

// ---------- reservations ----------

const resForm = $("res-form");
const resId = $("res-id");
const resGuest = $("res-guest");
const resPhone = $("res-phone");
const resCheckin = $("res-checkin");
const resCheckout = $("res-checkout");
const resSave = $("res-save");
const resCancel = $("res-cancel");
const resBody = $("res-body");
const resQuote = $("res-quote");

function renderReservations() {
  resBody.innerHTML = "";
  if (!state.reservations.length) {
    emptyRow(resBody, 8, "No bookings yet.");
    return;
  }
  for (const r of state.reservations) {
    const nights = nightsBetween(r.check_in, r.check_out);
    const tr = resBody.insertRow();
    if (r.check_out <= today()) tr.className = "past";
    [
      r.room_number,
      r.guest_name,
      r.guest_phone || "—",
      fmtDate(r.check_in),
      fmtDate(r.check_out),
      nights,
      money.format(nights * r.price),
    ].forEach((text) => (tr.insertCell().textContent = text));

    const actions = tr.insertCell();
    actions.className = "row-actions";
    actions.append(
      button("Edit", () => editReservation(r)),
      button("Delete", () => deleteReservation(r), "danger")
    );
  }
}

function editReservation(r) {
  resId.value = r.id;
  resRoomSelect.value = r.room_id;
  resGuest.value = r.guest_name;
  resPhone.value = r.guest_phone;
  resCheckin.value = r.check_in;
  resCheckout.value = r.check_out;
  resSave.textContent = "Update booking";
  resCancel.hidden = false;
  syncDateLimits();
  resGuest.focus();
}

async function deleteReservation(r) {
  if (!confirm(`Delete the booking for ${r.guest_name}?`)) return;
  try {
    await api(`/reservations/${r.id}`, { method: "DELETE" });
    toast(`Booking for ${r.guest_name} deleted.`);
    if (resId.value === String(r.id)) resetResForm();
    refresh();
  } catch (err) {
    toast(err.message, "error");
  }
}

/**
 * Cross-field date rules the browser can enforce natively: new stays cannot
 * start in the past, and check-out is always at least one night later.
 */
function syncDateLimits() {
  resCheckin.min = resId.value ? "" : today();
  resCheckout.min = resCheckin.value
    ? new Date(Date.parse(resCheckin.value) + 86400000).toISOString().slice(0, 10)
    : resCheckin.min;

  const nights = resCheckin.value && resCheckout.value
    ? nightsBetween(resCheckin.value, resCheckout.value)
    : 0;
  resCheckout.setCustomValidity(
    nights > 365 ? "A stay cannot be longer than 365 nights." : ""
  );
  updateQuote(nights);
}

function updateQuote(nights) {
  const room = state.rooms.find((r) => String(r.id) === resRoomSelect.value);
  resQuote.hidden = !(room && nights > 0);
  if (resQuote.hidden) return;
  resQuote.textContent =
    `${nights} night${nights === 1 ? "" : "s"} in room ${room.room_number}` +
    ` × ${money.format(room.price)} = ${money.format(nights * room.price)}`;
}

resForm.addEventListener("input", syncDateLimits);

function resetResForm() {
  resForm.reset();
  resId.value = "";
  resSave.textContent = "Book";
  resCancel.hidden = true;
  syncDateLimits();
  clearErrors(resForm);
}

resForm.onsubmit = (e) => {
  e.preventDefault();
  syncDateLimits();
  if (!showErrors(resForm, true)) return;
  const id = resId.value;
  const body = {
    room_id: parseInt(resRoomSelect.value, 10),
    guest_name: resGuest.value.trim(),
    guest_phone: resPhone.value.trim(),
    check_in: resCheckin.value,
    check_out: resCheckout.value,
  };
  submitting(resSave, async () => {
    await api(id ? `/reservations/${id}` : "/reservations", jsonOptions(id ? "PUT" : "POST", body));
    toast(id ? "Booking updated." : `Room booked for ${body.guest_name}.`);
    resetResForm();
    await refresh();
  });
};

resCancel.onclick = resetResForm;

// ---------- startup ----------

async function refresh() {
  try {
    const [rooms, reservations] = await Promise.all([api("/rooms"), api("/reservations")]);
    state.rooms = rooms;
    state.reservations = reservations;
    renderRooms();
    renderReservations();
    const occupied = state.rooms.filter((room) =>
      state.reservations.some(
        (r) => r.room_id === room.id && r.check_in <= today() && r.check_out > today()
      )
    ).length;
    $("summary").textContent =
      `${state.rooms.length} rooms · ${occupied} occupied today · ` +
      `${state.reservations.length} bookings`;
  } catch (err) {
    $("summary").textContent = "Could not reach the server.";
    toast(err.message, "error");
  }
}

syncDateLimits();
refresh();
