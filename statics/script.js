async function api(path, options) {
  const res = await fetch("/api" + path, options);
  const data = await res.json();
  if (!res.ok) {
    alert(data.error || "Request failed");
    throw new Error(data.error);
  }
  return data;
}

function jsonOptions(method, body) {
  return {
    method,
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  };
}

// ---------- rooms ----------

const roomForm = document.getElementById("room-form");
const roomId = document.getElementById("room-id");
const roomNumber = document.getElementById("room-number");
const roomType = document.getElementById("room-type");
const roomPrice = document.getElementById("room-price");
const roomSave = document.getElementById("room-save");
const roomCancel = document.getElementById("room-cancel");
const roomsBody = document.getElementById("rooms-body");
const resRoomSelect = document.getElementById("res-room");

async function loadRooms() {
  const rooms = await api("/rooms");
  roomsBody.innerHTML = "";
  resRoomSelect.innerHTML = '<option value="">Select room</option>';
  for (const room of rooms) {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td></td><td></td><td></td>
      <td>
        <button data-action="edit">Edit</button>
        <button data-action="delete">Delete</button>
      </td>`;
    tr.children[0].textContent = room.room_number;
    tr.children[1].textContent = room.room_type;
    tr.children[2].textContent = room.price.toFixed(2);
    tr.querySelector('[data-action="edit"]').onclick = () => {
      roomId.value = room.id;
      roomNumber.value = room.room_number;
      roomType.value = room.room_type;
      roomPrice.value = room.price;
      roomSave.textContent = "Update Room";
      roomCancel.hidden = false;
    };
    tr.querySelector('[data-action="delete"]').onclick = async () => {
      if (!confirm(`Delete room ${room.room_number}?`)) return;
      await api(`/rooms/${room.id}`, { method: "DELETE" });
      refresh();
    };
    roomsBody.appendChild(tr);

    const opt = document.createElement("option");
    opt.value = room.id;
    opt.textContent = `${room.room_number} (${room.room_type})`;
    resRoomSelect.appendChild(opt);
  }
}

function resetRoomForm() {
  roomForm.reset();
  roomId.value = "";
  roomSave.textContent = "Add Room";
  roomCancel.hidden = true;
}

roomForm.onsubmit = async (e) => {
  e.preventDefault();
  const body = {
    room_number: roomNumber.value.trim(),
    room_type: roomType.value,
    price: parseFloat(roomPrice.value),
  };
  const id = roomId.value;
  await api(id ? `/rooms/${id}` : "/rooms", jsonOptions(id ? "PUT" : "POST", body));
  resetRoomForm();
  refresh();
};

roomCancel.onclick = resetRoomForm;

// ---------- reservations ----------

const resForm = document.getElementById("res-form");
const resId = document.getElementById("res-id");
const resGuest = document.getElementById("res-guest");
const resPhone = document.getElementById("res-phone");
const resCheckin = document.getElementById("res-checkin");
const resCheckout = document.getElementById("res-checkout");
const resSave = document.getElementById("res-save");
const resCancel = document.getElementById("res-cancel");
const resBody = document.getElementById("res-body");

async function loadReservations() {
  const reservations = await api("/reservations");
  resBody.innerHTML = "";
  for (const r of reservations) {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td></td><td></td><td></td><td></td><td></td>
      <td>
        <button data-action="edit">Edit</button>
        <button data-action="delete">Delete</button>
      </td>`;
    const cells = [r.room_number, r.guest_name, r.guest_phone, r.check_in, r.check_out];
    cells.forEach((text, i) => (tr.children[i].textContent = text));
    tr.querySelector('[data-action="edit"]').onclick = () => {
      resId.value = r.id;
      resRoomSelect.value = r.room_id;
      resGuest.value = r.guest_name;
      resPhone.value = r.guest_phone;
      resCheckin.value = r.check_in;
      resCheckout.value = r.check_out;
      resSave.textContent = "Update Booking";
      resCancel.hidden = false;
    };
    tr.querySelector('[data-action="delete"]').onclick = async () => {
      if (!confirm(`Delete booking for ${r.guest_name}?`)) return;
      await api(`/reservations/${r.id}`, { method: "DELETE" });
      loadReservations();
    };
    resBody.appendChild(tr);
  }
}

function resetResForm() {
  resForm.reset();
  resId.value = "";
  resSave.textContent = "Book";
  resCancel.hidden = true;
}

resForm.onsubmit = async (e) => {
  e.preventDefault();
  const body = {
    room_id: parseInt(resRoomSelect.value),
    guest_name: resGuest.value.trim(),
    guest_phone: resPhone.value.trim(),
    check_in: resCheckin.value,
    check_out: resCheckout.value,
  };
  const id = resId.value;
  await api(id ? `/reservations/${id}` : "/reservations", jsonOptions(id ? "PUT" : "POST", body));
  resetResForm();
  loadReservations();
};

resCancel.onclick = resetResForm;

function refresh() {
  loadRooms();
  loadReservations();
}

refresh();
