document.addEventListener("DOMContentLoaded", () => {
  const activitiesList = document.getElementById("activities-list");
  const activitySelect = document.getElementById("activity");
  const signupForm = document.getElementById("signup-form");
  const teacherAccessMessage = document.getElementById("teacher-access-message");
  const messageDiv = document.getElementById("message");
  const accountMenuButton = document.getElementById("account-menu-button");
  const accountMenu = document.getElementById("account-menu");
  const accountStatus = document.getElementById("account-status");
  const loginOpenButton = document.getElementById("login-open-button");
  const logoutButton = document.getElementById("logout-button");
  const loginDialog = document.getElementById("login-dialog");
  const loginForm = document.getElementById("login-form");
  const loginCancelButton = document.getElementById("login-cancel-button");
  const loginError = document.getElementById("login-error");
  let isTeacher = false;
  let messageTimeout;

  function showMessage(text, kind) {
    messageDiv.textContent = text;
    messageDiv.className = kind;
    messageDiv.classList.remove("hidden");

    clearTimeout(messageTimeout);
    messageTimeout = setTimeout(() => {
      messageDiv.classList.add("hidden");
    }, 5000);
  }

  function setTeacherSession(authenticated, username = "") {
    isTeacher = authenticated;
    signupForm.classList.toggle("hidden", !authenticated);
    teacherAccessMessage.classList.toggle("hidden", authenticated);
    loginOpenButton.classList.toggle("hidden", authenticated);
    logoutButton.classList.toggle("hidden", !authenticated);
    accountStatus.textContent = authenticated
      ? `Signed in: ${username}`
      : "Not signed in";
  }

  async function refreshTeacherSession() {
    try {
      const response = await fetch("/auth/session");
      const session = await response.json();
      if (!response.ok) {
        throw new Error(session.detail || "Unable to check teacher login.");
      }
      setTeacherSession(session.authenticated, session.username || "");
    } catch (error) {
      setTeacherSession(false);
      console.error("Error checking teacher login:", error);
    }
  }

  async function fetchActivities() {
    try {
      const response = await fetch("/activities");
      if (!response.ok) {
        throw new Error("Unable to load activities.");
      }
      const activities = await response.json();

      activitiesList.replaceChildren();
      activitySelect.replaceChildren(new Option("-- Select an activity --", ""));

      Object.entries(activities).forEach(([name, details]) => {
        const activityCard = document.createElement("div");
        activityCard.className = "activity-card";

        const title = document.createElement("h4");
        title.textContent = name;
        activityCard.appendChild(title);

        const description = document.createElement("p");
        description.textContent = details.description;
        activityCard.appendChild(description);

        const schedule = document.createElement("p");
        const scheduleLabel = document.createElement("strong");
        scheduleLabel.textContent = "Schedule: ";
        schedule.append(scheduleLabel, document.createTextNode(details.schedule));
        activityCard.appendChild(schedule);

        const spotsLeft = details.max_participants - details.participants.length;
        const availability = document.createElement("p");
        const availabilityLabel = document.createElement("strong");
        availabilityLabel.textContent = "Availability: ";
        availability.append(
          availabilityLabel,
          document.createTextNode(`${spotsLeft} spots left`)
        );
        activityCard.appendChild(availability);

        const participantsContainer = document.createElement("div");
        participantsContainer.className = "participants-container";
        const participantsHeading = document.createElement("h5");
        participantsHeading.textContent = "Participants:";
        participantsContainer.appendChild(participantsHeading);

        if (details.participants.length > 0) {
          const participantsList = document.createElement("ul");
          participantsList.className = "participants-list";

          details.participants.forEach((email) => {
            const participant = document.createElement("li");
            const participantEmail = document.createElement("span");
            participantEmail.className = "participant-email";
            participantEmail.textContent = email;
            participant.appendChild(participantEmail);

            if (isTeacher) {
              const unregisterButton = document.createElement("button");
              unregisterButton.type = "button";
              unregisterButton.className = "delete-btn";
              unregisterButton.textContent = "Remove";
              unregisterButton.setAttribute(
                "aria-label",
                `Unregister ${email} from ${name}`
              );
              unregisterButton.addEventListener("click", handleUnregister);
              unregisterButton.dataset.activity = name;
              unregisterButton.dataset.email = email;
              participant.appendChild(unregisterButton);
            }

            participantsList.appendChild(participant);
          });
          participantsContainer.appendChild(participantsList);
        } else {
          const noParticipants = document.createElement("p");
          noParticipants.textContent = "No participants yet";
          participantsContainer.appendChild(noParticipants);
        }

        activityCard.appendChild(participantsContainer);
        activitiesList.appendChild(activityCard);

        const option = document.createElement("option");
        option.value = name;
        option.textContent = name;
        activitySelect.appendChild(option);
      });
    } catch (error) {
      activitiesList.textContent =
        "Failed to load activities. Please try again later.";
      console.error("Error fetching activities:", error);
    }
  }

  async function handleUnregister(event) {
    if (!isTeacher) {
      showMessage("Teacher login is required to unregister students.", "error");
      return;
    }

    const button = event.currentTarget;
    const activity = button.dataset.activity;
    const email = button.dataset.email;

    try {
      const response = await fetch(
        `/activities/${encodeURIComponent(
          activity
        )}/unregister?email=${encodeURIComponent(email)}`,
        { method: "DELETE" }
      );
      const result = await response.json();

      if (!response.ok) {
        throw new Error(result.detail || "Unable to unregister student.");
      }

      showMessage(result.message, "success");
      await fetchActivities();
    } catch (error) {
      showMessage(error.message || "Failed to unregister. Please try again.", "error");
      console.error("Error unregistering:", error);
    }
  }

  accountMenuButton.addEventListener("click", () => {
    const isExpanded = accountMenuButton.getAttribute("aria-expanded") === "true";
    accountMenuButton.setAttribute("aria-expanded", String(!isExpanded));
    accountMenu.classList.toggle("hidden", isExpanded);
  });

  loginOpenButton.addEventListener("click", () => {
    accountMenu.classList.add("hidden");
    accountMenuButton.setAttribute("aria-expanded", "false");
    loginError.classList.add("hidden");
    loginDialog.showModal();
  });

  loginCancelButton.addEventListener("click", () => loginDialog.close());

  loginForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    loginError.classList.add("hidden");

    const formData = new FormData(loginForm);
    try {
      const response = await fetch("/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          username: formData.get("username"),
          password: formData.get("password"),
        }),
      });
      const result = await response.json();

      if (!response.ok) {
        throw new Error(result.detail || "Unable to sign in.");
      }

      setTeacherSession(true, result.username);
      loginForm.reset();
      loginDialog.close();
      await fetchActivities();
      showMessage("Signed in successfully.", "success");
    } catch (error) {
      loginError.textContent = error.message || "Unable to sign in.";
      loginError.classList.remove("hidden");
    }
  });

  logoutButton.addEventListener("click", async () => {
    try {
      const response = await fetch("/auth/logout", { method: "POST" });
      const result = await response.json();
      if (!response.ok) {
        throw new Error(result.detail || "Unable to log out.");
      }

      setTeacherSession(false);
      accountMenu.classList.add("hidden");
      accountMenuButton.setAttribute("aria-expanded", "false");
      await fetchActivities();
      showMessage(result.message, "success");
    } catch (error) {
      showMessage(error.message || "Unable to log out.", "error");
      console.error("Error logging out:", error);
    }
  });

  signupForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    if (!isTeacher) {
      showMessage("Teacher login is required to register students.", "error");
      return;
    }

    const email = document.getElementById("email").value;
    const activity = activitySelect.value;

    try {
      const response = await fetch(
        `/activities/${encodeURIComponent(
          activity
        )}/signup?email=${encodeURIComponent(email)}`,
        { method: "POST" }
      );
      const result = await response.json();

      if (!response.ok) {
        throw new Error(result.detail || "Unable to register student.");
      }

      showMessage(result.message, "success");
      signupForm.reset();
      await fetchActivities();
    } catch (error) {
      showMessage(error.message || "Failed to sign up. Please try again.", "error");
      console.error("Error signing up:", error);
    }
  });

  refreshTeacherSession().then(fetchActivities);
});
