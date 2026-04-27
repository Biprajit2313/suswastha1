(function () {
  "use strict";

  var AUTH_KEY = "suswastha_auth";
  var USER_KEY = "suswastha_user";
  var LEGACY_EMAIL_KEY = "suswastha_email";
  var TOKEN_KEY = "suswastha_token";

  var PUBLIC_PAGES = [
    "index.html",
    "login.html",
    "signup.html",
    "about.html",
    "contact-about.html",
    "forgot-password.html",
  ];

  function getCurrentPage() {
    var path = window.location.pathname || "";
    var page = path.substring(path.lastIndexOf("/") + 1).toLowerCase();
    return page || "index.html";
  }

  function getStoredUser() {
    var raw = localStorage.getItem(USER_KEY);
    if (!raw) return null;
    try {
      return JSON.parse(raw);
    } catch (err) {
      return null;
    }
  }

  function isLoggedIn() {
    if (localStorage.getItem(AUTH_KEY) === "true" || localStorage.getItem(TOKEN_KEY)) return true;
    return Boolean(localStorage.getItem(LEGACY_EMAIL_KEY));
  }

  function loginUser(userData) {
    localStorage.setItem(AUTH_KEY, "true");
    var user = {
      email: (userData && userData.email) || localStorage.getItem(LEGACY_EMAIL_KEY) || "",
      role: (userData && userData.role) || "user",
      name: (userData && userData.name) || "",
    };
    localStorage.setItem(USER_KEY, JSON.stringify(user));
    if (userData && userData.access_token) {
      localStorage.setItem(TOKEN_KEY, userData.access_token);
    }
    if (user.email) localStorage.setItem(LEGACY_EMAIL_KEY, user.email);
    window.location.href = "dashboard.html";
  }

  function logoutUser() {
    localStorage.removeItem(AUTH_KEY);
    localStorage.removeItem(USER_KEY);
    localStorage.removeItem(LEGACY_EMAIL_KEY);
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem("suswastha_profile");
    window.location.href = "index.html";
  }

  function isPublicPage(page) {
    return PUBLIC_PAGES.indexOf(page) !== -1;
  }

  function checkAuth() {
    var page = getCurrentPage();
    var loggedIn = isLoggedIn();

    if (!loggedIn && !isPublicPage(page)) {
      window.location.href = "login.html";
      return false;
    }

    if (loggedIn && (page === "login.html" || page === "signup.html")) {
      window.location.href = "dashboard.html";
      return false;
    }

    if (loggedIn && page === "admin.html") {
      var user = getStoredUser();
      if (user && user.role && user.role !== "admin") {
        window.location.href = "dashboard.html";
        return false;
      }
    }

    return true;
  }

  function createNavAnchor(className, href, text, id) {
    var a = document.createElement("a");
    if (className) a.className = className;
    a.href = href;
    a.textContent = text;
    if (id) a.id = id;
    return a;
  }

  function updateNavbar() {
    var loggedIn = isLoggedIn();
    var loginLinks = Array.prototype.slice.call(
      document.querySelectorAll('a[href="login.html"]')
    );
    var signupLinks = Array.prototype.slice.call(
      document.querySelectorAll('a[href="signup.html"]')
    );
    var dashboardLinks = Array.prototype.slice.call(
      document.querySelectorAll('a[href="dashboard.html"]')
    );
    var logoutLinks = Array.prototype.slice.call(
      document.querySelectorAll('[data-auth="logout"]')
    );
    var navMenus = Array.prototype.slice.call(document.querySelectorAll(".nav-links"));

    loginLinks.forEach(function (el) {
      el.style.display = loggedIn ? "none" : "";
    });
    signupLinks.forEach(function (el) {
      el.style.display = loggedIn ? "none" : "";
    });

    // For module top actions where only login/signup exist, inject dashboard/logout once.
    var actionContainers = document.querySelectorAll(".module-actions, .auth-actions");
    actionContainers.forEach(function (container) {
      var hasDashboard = container.querySelector('a[href="dashboard.html"]');
      var hasLogout = container.querySelector('[data-auth="logout"]');

      if (!hasDashboard) {
        var dash = createNavAnchor("btn ghost", "dashboard.html", "Dashboard", "dashboardNav");
        dash.style.display = loggedIn ? "" : "none";
        container.appendChild(dash);
      } else {
        hasDashboard.style.display = loggedIn ? "" : "none";
      }

      if (!hasLogout) {
        var logout = createNavAnchor("btn primary", "#", "Logout", "logoutNav");
        logout.setAttribute("data-auth", "logout");
        logout.style.display = loggedIn ? "" : "none";
        logout.addEventListener("click", function (event) {
          event.preventDefault();
          logoutUser();
        });
        container.appendChild(logout);
      } else {
        hasLogout.style.display = loggedIn ? "" : "none";
      }
    });

    navMenus.forEach(function (nav) {
      var hasProfile = nav.querySelector('a[href="profile.html"]');
      var hasScan = nav.querySelector('a[href="scan.html"]');
      if (!hasProfile) {
        var profileLink = createNavAnchor("", "profile.html", "Profile");
        profileLink.setAttribute("data-auth-link", "protected");
        profileLink.style.display = loggedIn ? "" : "none";
        nav.appendChild(profileLink);
      } else {
        hasProfile.style.display = loggedIn ? "" : "none";
      }

      if (!hasScan) {
        var scanLink = createNavAnchor("", "scan.html", "Scan Report");
        scanLink.setAttribute("data-auth-link", "protected");
        scanLink.style.display = loggedIn ? "" : "none";
        nav.appendChild(scanLink);
      } else {
        hasScan.style.display = loggedIn ? "" : "none";
      }
    });

    dashboardLinks.forEach(function (el) {
      if (el.closest(".module-actions") || el.closest(".auth-actions")) return;
      el.style.display = loggedIn ? "" : el.style.display;
    });

    logoutLinks.forEach(function (el) {
      el.style.display = loggedIn ? "" : "none";
      if (!el.dataset.bound) {
        el.addEventListener("click", function (event) {
          event.preventDefault();
          logoutUser();
        });
        el.dataset.bound = "true";
      }
    });
  }

  document.addEventListener("DOMContentLoaded", function () {
    checkAuth();
    updateNavbar();
  });

  window.checkAuth = checkAuth;
  window.isLoggedIn = isLoggedIn;
  window.loginUser = loginUser;
  window.logoutUser = logoutUser;
  window.updateNavbar = updateNavbar;
  window.getAuthToken = function () {
    return localStorage.getItem(TOKEN_KEY) || "";
  };
})();
