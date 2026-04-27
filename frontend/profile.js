(function () {
  "use strict";

  const REPORTS_KEY = "suswastha_reports";
  const SUGGESTIONS = {
    diabetes: ["Reduce sugar intake", "Exercise daily for 30 minutes"],
    sugar: ["Avoid sugary drinks", "Track fasting glucose regularly"],
    bp: ["Reduce salt intake", "Monitor blood pressure every day"],
    cholesterol: ["Avoid trans fats", "Increase fiber-rich foods"],
  };

  function getCurrentEmail() {
    return localStorage.getItem("suswastha_email") || "";
  }

  function getReportsByEmail(email) {
    try {
      const all = JSON.parse(localStorage.getItem(REPORTS_KEY) || "[]");
      return all.filter((item) => item.email === email);
    } catch {
      return [];
    }
  }

  function generatePdf(report, email) {
    const jspdf = window.jspdf;
    if (!jspdf || !jspdf.jsPDF) {
      alert("jsPDF library not loaded.");
      return;
    }
    const doc = new jspdf.jsPDF();
    doc.setFontSize(14);
    doc.text("SuSwastha Medical Report", 14, 20);
    doc.setFontSize(11);
    doc.text(`Email: ${email}`, 14, 35);
    doc.text(`Test: ${report.test || "-"}`, 14, 45);
    doc.text(`Result: ${report.result || "-"}`, 14, 55);
    doc.text(`Date: ${report.date || "-"}`, 14, 65);
    doc.save(`suswastha-report-${Date.now()}.pdf`);
  }

  function sendViaEmailJS(report, email) {
    if (!window.emailjs) {
      alert("EmailJS library not loaded.");
      return;
    }

    // Replace placeholders with your EmailJS credentials after setup.
    const serviceId = "YOUR_SERVICE_ID";
    const templateId = "YOUR_TEMPLATE_ID";
    const publicKey = "YOUR_PUBLIC_KEY";
    window.emailjs.init({ publicKey });

    window.emailjs
      .send(serviceId, templateId, {
        to_email: email,
        user_email: email,
        test_name: report.test || "-",
        result: report.result || "-",
        date: report.date || "-",
      })
      .then(() => alert("Report sent to email successfully."))
      .catch(() => alert("Email send failed. Configure EmailJS keys."));
  }

  function renderSuggestions(reports) {
    const suggestionTarget = document.getElementById("profile-suggestions");
    if (!suggestionTarget) return;

    const diseaseKeys = new Set();
    reports.forEach((report) => {
      const text = `${report.test || ""} ${report.result || ""}`.toLowerCase();
      Object.keys(SUGGESTIONS).forEach((key) => {
        if (text.includes(key)) diseaseKeys.add(key);
      });
    });

    const allSuggestions = [];
    diseaseKeys.forEach((key) => {
      SUGGESTIONS[key].forEach((tip) => allSuggestions.push(tip));
    });

    suggestionTarget.innerHTML = allSuggestions.length
      ? allSuggestions.map((tip) => `<li>${tip}</li>`).join("")
      : "<li>No disease-specific suggestions yet.</li>";
  }

  function renderReports() {
    const email = getCurrentEmail();
    const emailTarget = document.getElementById("profile-email");
    const body = document.getElementById("profile-reports-body");
    if (emailTarget) emailTarget.textContent = email || "-";
    if (!body) return;

    if (!email) {
      body.innerHTML = `<tr><td colspan="5">Please login to view your profile.</td></tr>`;
      return;
    }

    const reports = getReportsByEmail(email);
    if (!reports.length) {
      body.innerHTML = `<tr><td colspan="5">No reports found.</td></tr>`;
      renderSuggestions([]);
      return;
    }

    body.innerHTML = reports
      .map(
        (report, index) => `
        <tr>
          <td>${report.test || "-"}</td>
          <td>${report.result || "-"}</td>
          <td>${report.date || "-"}</td>
          <td><button class="btn ghost profile-pdf-btn" data-index="${index}">Download PDF</button></td>
          <td><button class="btn primary profile-email-btn" data-index="${index}">Send to Email</button></td>
        </tr>
      `
      )
      .join("");

    renderSuggestions(reports);

    body.querySelectorAll(".profile-pdf-btn").forEach((btn) => {
      btn.addEventListener("click", () => {
        const report = reports[Number(btn.dataset.index)];
        generatePdf(report, email);
      });
    });

    body.querySelectorAll(".profile-email-btn").forEach((btn) => {
      btn.addEventListener("click", () => {
        const report = reports[Number(btn.dataset.index)];
        sendViaEmailJS(report, email);
      });
    });
  }

  document.addEventListener("DOMContentLoaded", renderReports);
})();
