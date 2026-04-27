const express = require("express");
const cors = require("cors");
const nodemailer = require("nodemailer");

const app = express();
const PORT = process.env.PORT || 3001;
const OTP_TTL_MS = 5 * 60 * 1000;

app.use(cors());
app.use(express.json());

// In-memory OTP store: key => { otp, expiresAt, purpose, password, name, dob }
const otpStore = new Map();
const users = [];
const bookings = [];

function validateEmail(email) {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test((email || "").trim());
}

function validatePassword(password) {
  return /^(?=.*\d).{6,}$/.test(password || "");
}

function makeOtp() {
  return String(Math.floor(100000 + Math.random() * 900000));
}

async function sendOtpEmail(email, otp) {
  const host = process.env.SMTP_HOST;
  const user = process.env.SMTP_USER;
  const pass = process.env.SMTP_PASS;
  const from = process.env.SMTP_FROM || user;
  if (!host || !user || !pass) {
    console.log(`[OTP Simulation] ${email} -> ${otp}`);
    return { simulated: true };
  }

  const transporter = nodemailer.createTransport({
    host,
    port: Number(process.env.SMTP_PORT || 587),
    secure: false,
    auth: { user, pass },
  });

  await transporter.sendMail({
    from,
    to: email,
    subject: "SuSwastha OTP Verification",
    text: `Your SuSwastha OTP is ${otp}. It expires in 5 minutes.`,
  });
  return { simulated: false };
}

app.get("/api/health", (req, res) => {
  res.json({ ok: true });
});

app.post("/api/auth/send-otp", async (req, res) => {
  const { email, purpose, password, name, dob } = req.body || {};
  const normalizedEmail = String(email || "").trim().toLowerCase();
  const normalizedPurpose = String(purpose || "").trim().toLowerCase();
  if (!validateEmail(normalizedEmail)) {
    return res.status(400).json({ error: "Enter a valid email address." });
  }
  if (!["signup", "login"].includes(normalizedPurpose)) {
    return res.status(400).json({ error: "Invalid OTP request." });
  }

  const existingUser = users.find((u) => u.email === normalizedEmail);
  if (normalizedPurpose === "signup" && existingUser) {
    return res.status(409).json({ error: "Email already exists. Please login." });
  }
  if (normalizedPurpose === "login" && !existingUser) {
    return res.status(404).json({ error: "Account not found. Please sign up first." });
  }
  if (normalizedPurpose === "signup") {
    if (!name || !String(name).trim()) {
      return res.status(400).json({ error: "Name is required." });
    }
    if (!validatePassword(password)) {
      return res.status(400).json({ error: "Password must be 6+ chars with at least one number." });
    }
  } else if (existingUser && existingUser.password !== String(password || "")) {
    return res.status(401).json({ error: "Incorrect password." });
  }

  const otp = makeOtp();
  otpStore.set(normalizedEmail, {
    otp,
    expiresAt: Date.now() + OTP_TTL_MS,
    purpose: normalizedPurpose,
    password: String(password || ""),
    name: String(name || "").trim(),
    dob: String(dob || "").trim(),
  });

  const sent = await sendOtpEmail(normalizedEmail, otp);
  return res.json({
    message: sent.simulated
      ? "OTP generated in server console (simulation mode)."
      : "OTP sent to your email.",
  });
});

app.post("/api/auth/verify-otp", (req, res) => {
  const { email, otp, purpose } = req.body || {};
  const normalizedEmail = String(email || "").trim().toLowerCase();
  const normalizedPurpose = String(purpose || "").trim().toLowerCase();
  const payload = otpStore.get(normalizedEmail);
  if (!payload) return res.status(400).json({ error: "OTP not requested." });
  if (payload.expiresAt < Date.now()) {
    otpStore.delete(normalizedEmail);
    return res.status(400).json({ error: "OTP expired. Request a new one." });
  }
  if (payload.purpose !== normalizedPurpose) {
    return res.status(400).json({ error: "OTP purpose mismatch." });
  }
  if (String(otp || "").trim() !== payload.otp) {
    return res.status(400).json({ error: "Invalid OTP." });
  }

  let user = users.find((u) => u.email === normalizedEmail);
  if (normalizedPurpose === "signup") {
    if (user) {
      otpStore.delete(normalizedEmail);
      return res.status(409).json({ error: "Email already exists. Please login." });
    }
    user = {
      id: Date.now(),
      name: payload.name,
      email: normalizedEmail,
      password: payload.password,
      dob: payload.dob || "",
      role: normalizedEmail.includes("admin") ? "admin" : "user",
      createdAt: new Date().toISOString(),
    };
    users.push(user);
  }

  if (!user) {
    otpStore.delete(normalizedEmail);
    return res.status(404).json({ error: "Account not found." });
  }

  otpStore.delete(normalizedEmail);
  return res.json({
    message: "Authentication successful.",
    user: {
      name: user.name || "",
      email: user.email,
      role: user.role || "user",
      dob: user.dob || "",
    },
  });
});

app.post("/api/bookings", (req, res) => {
  const { name, email, problem, date, time, doctor } = req.body || {};
  if (!name || !email || !problem || !date || !time || !doctor) {
    return res.status(400).json({ error: "All fields are required." });
  }
  if (!validateEmail(email)) {
    return res.status(400).json({ error: "Enter a valid email address." });
  }

  const booking = {
    id: Date.now(),
    name: String(name).trim(),
    email: String(email).trim().toLowerCase(),
    problem: String(problem).trim(),
    date: String(date),
    time: String(time),
    doctor: String(doctor).trim(),
    createdAt: new Date().toISOString(),
  };
  bookings.unshift(booking);

  return res.json({ message: "Doctor booked successfully.", booking });
});

app.get("/api/bookings", (req, res) => {
  const email = String(req.query.email || "").trim().toLowerCase();
  if (!email) return res.json(bookings.slice(0, 50));
  return res.json(bookings.filter((b) => b.email === email).slice(0, 50));
});

app.listen(PORT, () => {
  console.log(`SuSwastha Node API running on http://localhost:${PORT}`);
});
