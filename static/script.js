document.addEventListener("DOMContentLoaded", () => {
  // ✅ Handle Signup
  const signupForm = document.getElementById("survey-form");
  if (signupForm) {
    signupForm.addEventListener("submit", async (event) => {
      event.preventDefault();

      const password = document.getElementById("password").value;
      const confirmPassword = document.getElementById("confirm-password").value;

      if (password !== confirmPassword) {
        alert("Passwords do not match! Please check your Confirm Password.");
        return;
      }

      const formData = {
        name: document.getElementById("name").value,
        email: document.getElementById("email").value,
        role: document.getElementById("dropdown").value,
        password: password,
      };

      const response = await fetch("http://localhost:5000/signup", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(formData),
      });

      console.log("📩 Signup Response Status:", response.status);
      if (!response.ok) {
        const errorData = await response.json();
        console.error("Signup Error:", errorData);
        alert(errorData.message || "Signup failed!");
        return;
      }

      const result = await response.json();
      alert(result.message);
      window.location.href = "home.html";
    });
  } else {
    console.warn("⚠️ Signup form not found. Skipping signup event listener.");
  }

  // ✅ Handle Login & Redirect Based on Role
  const loginForm = document.getElementById("login-form");
  if (loginForm) {
    loginForm.addEventListener("submit", async (event) => {
      event.preventDefault();

      const email = document.getElementById("email").value;
      const password = document.querySelector("#login-form input[type='password']").value; // Fixed password selector

      const response = await fetch("http://localhost:5000/login", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ email, password }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        console.error("Login Error:", errorData);
        alert(errorData.message || "Login failed!");
        return;
      }

      const result = await response.json();
      localStorage.setItem("token", result.token); // ✅ Store JWT Token

      // ✅ Redirect Based on Role
      const role = result.role;
      const dashboardMap = {
        "Hospital Administrator": "hospital_dashboard.html",
        "Healthcare Providers": "healthcare_dashboard.html",
        "Insurance Companies": "insurance_dashboard.html",
        "Legal Professionals": "legal_dashboard.html",
        "Patients & Family Members": "patient_dashboard.html",
        "Law Enforcement Officials": "law_dashboard.html",
      };

      window.location.href = dashboardMap[role] || "home.html";
    });
  } else {
    console.warn("⚠️ Login form not found. Skipping login event listener.");
  }

  // ✅ Fetch User Details for Dashboard (After Login)
  const token = localStorage.getItem("token");
  if (token) {
    fetch("http://localhost:5000/api/getUserDetails", {
      method: "GET",
      headers: {
        "Authorization": `Bearer ${token}`, // Send token in Authorization header
      },
    })
    .then(response => response.json())
    .then(data => {
      if (data.name) {
        document.getElementById("user-name").textContent = data.name; // Set user name
        document.getElementById("role").textContent = data.role; // Set user role
      }
    })
    .catch(error => console.error("Error fetching user data:", error));
  }
});
