(function () {
  "use strict";

  const BOOKING_API_BASE =
    (window.SUSWASTHA_CONFIG && window.SUSWASTHA_CONFIG.nodeBaseUrl) ||
    (window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1"
      ? "http://127.0.0.1:3001"
      : "https://suswastha-node.onrender.com");

  function renderBookings(list) {
    const target = document.getElementById("booking-history");
    if (!target) return;
    if (!Array.isArray(list) || list.length === 0) {
      target.innerHTML = "<p>No bookings yet.</p>";
      return;
    }
    target.innerHTML = list
      .map(
        (b) => `
      <div style="margin-bottom: 12px; border-bottom: 1px solid #ddd; padding-bottom: 8px;">
        <strong>${b.doctor}</strong> - ${b.date} ${b.time}<br />
        <span>${b.problem}</span>
      </div>`
      )
      .join("");
  }

  async function loadBookings(email) {
    try {
      const res = await fetch(`${BOOKING_API_BASE}/api/bookings?email=${encodeURIComponent(email)}`);
      const data = await res.json();
      renderBookings(data);
    } catch (err) {
      console.error(err);
    }
  }

  function setupBookingPage() {
    const form = document.getElementById("booking-form");
    const status = document.getElementById("booking-status");
    if (!form || !status) return;

    const email = localStorage.getItem("suswastha_email") || "";
    const emailInput = form.querySelector('input[name="email"]');
    if (emailInput && email) emailInput.value = email;

    loadBookings(email);

    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      const formData = new FormData(form);
      const payload = {
        name: String(formData.get("name") || "").trim(),
        email: String(formData.get("email") || "").trim().toLowerCase(),
        problem: String(formData.get("problem") || "").trim(),
        date: String(formData.get("date") || ""),
        time: String(formData.get("time") || ""),
        doctor: String(formData.get("doctor") || "").trim(),
      };

      if (!payload.name || !payload.email || !payload.problem || !payload.date || !payload.time || !payload.doctor) {
        status.textContent = "Please fill all fields.";
        status.style.color = "#d93025";
        return;
      }

      try {
        const res = await fetch(`${BOOKING_API_BASE}/api/bookings`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        });
        const data = await res.json();
        if (!res.ok) {
          status.textContent = data.error || "Booking failed.";
          status.style.color = "#d93025";
          return;
        }
        status.textContent = data.message || "Booking confirmed.";
        status.style.color = "#0c8a43";
        form.reset();
        if (emailInput && payload.email) emailInput.value = payload.email;
        loadBookings(payload.email);
      } catch (err) {
        console.error(err);
        status.textContent = "Could not connect to booking service.";
        status.style.color = "#d93025";
      }
    });
  }

  document.addEventListener("DOMContentLoaded", setupBookingPage);
})();
