(function () {
  "use strict";

  const REPORTS_KEY = "suswastha_reports";
  const DISEASE_MAP = {
    diabetes: { test: "Diabetes", result: "Diabetes indicators detected" },
    sugar: { test: "Diabetes", result: "High sugar indicators detected" },
    bp: { test: "Blood Pressure", result: "BP indicators detected" },
    pressure: { test: "Blood Pressure", result: "BP indicators detected" },
    cholesterol: { test: "Cholesterol", result: "Cholesterol indicators detected" },
  };

  function parseDetectedDisease(text) {
    const lower = (text || "").toLowerCase();
    for (const key of Object.keys(DISEASE_MAP)) {
      if (lower.includes(key)) return DISEASE_MAP[key];
    }
    return { test: "General Medical Report", result: "Report scanned successfully" };
  }

  function saveDetectedReport(extractedText) {
    const email = localStorage.getItem("suswastha_email");
    if (!email) return false;

    const detected = parseDetectedDisease(extractedText);
    const entry = {
      email,
      test: detected.test,
      result: detected.result,
      date: new Date().toISOString().slice(0, 10),
      rawText: extractedText,
    };

    let reports = [];
    try {
      reports = JSON.parse(localStorage.getItem(REPORTS_KEY) || "[]");
    } catch {
      reports = [];
    }
    reports.unshift(entry);
    localStorage.setItem(REPORTS_KEY, JSON.stringify(reports));
    return true;
  }

  function setupScan() {
    const form = document.getElementById("scan-form");
    const fileInput = document.getElementById("scan-image");
    const output = document.getElementById("scan-output");
    const status = document.getElementById("scan-status");
    const saveBtn = document.getElementById("save-scan");

    if (!form || !fileInput || !output || !status || !saveBtn) return;

    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      const file = fileInput.files && fileInput.files[0];
      if (!file) {
        status.textContent = "Please capture or upload an image first.";
        return;
      }

      status.textContent = "Extracting text... please wait.";
      try {
        const result = await Tesseract.recognize(file, "eng");
        output.value = (result && result.data && result.data.text ? result.data.text : "").trim();
        status.textContent = "Scan complete.";
      } catch (err) {
        console.error(err);
        status.textContent = "OCR failed. Try a clearer image.";
      }
    });

    saveBtn.addEventListener("click", () => {
      const text = output.value.trim();
      if (!text) {
        status.textContent = "No extracted text available to save.";
        return;
      }
      const saved = saveDetectedReport(text);
      if (!saved) {
        status.textContent = "Please login first.";
        return;
      }
      const detected = parseDetectedDisease(text);
      status.textContent = `Report saved: ${detected.test} - ${detected.result}`;
    });
  }

  document.addEventListener("DOMContentLoaded", setupScan);
})();
