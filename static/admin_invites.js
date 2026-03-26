(function () {
  "use strict";

  const inviteModalWorkflows = new Map();
  const DEFAULT_INVITE_WORKFLOW = "default";
  const INVITATION_EMAIL_FAILED_MESSAGE =
    "Invitation created but email failed to send";

  function registerInviteModalWorkflow(name, { reset, setup } = {}) {
    inviteModalWorkflows.set(name, {
      reset: typeof reset === "function" ? reset : () => {},
      setup: typeof setup === "function" ? setup : () => {},
    });
  }

  function getInviteModalWorkflow(name) {
    return (
      inviteModalWorkflows.get(name) ||
      inviteModalWorkflows.get(DEFAULT_INVITE_WORKFLOW) || {
        reset: () => {},
        setup: () => {},
      }
    );
  }

  function resetInviteModalWorkflows() {
    inviteModalWorkflows.clear();
  }

  function getInviteModalWorkflowNames() {
    return Array.from(inviteModalWorkflows.keys());
  }

  async function loadPrograms() {
    try {
      const response = await fetch("/api/programs");
      if (!response.ok) {
        return;
      }
      const data = await response.json();
      if (!data.success) {
        return;
      }
      const programSelect = document.getElementById("invitePrograms");
      if (!programSelect) return;
      programSelect.innerHTML = "";

      data.programs.forEach((program) => {
        const option = document.createElement("option");
        option.value = program.id;
        option.textContent = program.name;
        programSelect.appendChild(option);
      });
    } catch (error) {
      console.warn("Error loading programs:", error);
    }
  }

  function setProgramSelectionVisibility(role) {
    const programSelection = document.getElementById("programSelection");
    const invitePrograms = document.getElementById("invitePrograms");
    if (!programSelection || !invitePrograms) return;

    if (role === "program_admin") {
      programSelection.style.display = "block";
      invitePrograms.required = true;
    } else {
      programSelection.style.display = "none";
      invitePrograms.required = false;
    }
  }

  function handleRoleSelectionChange(event) {
    setProgramSelectionVisibility(event.target.value);
  }

  function buildInvitationPayload(formData) {
    const data = {
      invitee_email: formData.get("invitee_email"),
      invitee_role: formData.get("invitee_role"),
      personal_message: formData.get("personal_message") || undefined,
    };
    const firstName = formData.get("first_name");
    const lastName = formData.get("last_name");
    if (firstName) data.first_name = firstName;
    if (lastName) data.last_name = lastName;

    if (data.invitee_role === "program_admin") {
      const programIds = Array.from(
        document.getElementById("invitePrograms").selectedOptions,
      ).map((option) => option.value);
      if (programIds.length > 0) {
        data.program_ids = programIds;
      }
    }

    const sectionId = formData.get("section_id");
    if (sectionId) {
      data.section_id = sectionId;
    }
    return data;
  }

  function getCsrfHeaders() {
    const csrfTokenMeta = document.querySelector('meta[name="csrf-token"]');
    const csrfToken = csrfTokenMeta ? csrfTokenMeta.content : null;
    return {
      "Content-Type": "application/json",
      ...(csrfToken && { "X-CSRFToken": csrfToken }),
    };
  }

  function isInvitationDeliveryFailedMessage(message) {
    return message === INVITATION_EMAIL_FAILED_MESSAGE;
  }

  function displayInvitationResult(message, detail, showWarning, showSuccess) {
    if (isInvitationDeliveryFailedMessage(message)) {
      showWarning(message);
    } else {
      showSuccess(message);
    }

    if (!detail) {
      return;
    }
    const alert = document.querySelector(".admin-message-dynamic");
    if (!alert) {
      return;
    }
    const detailEl = document.createElement("div");
    detailEl.className = "text-muted small mt-1";
    detailEl.textContent = `Reason: ${detail}`;
    alert.appendChild(detailEl);
  }

  function buildInviteModalContext(options, modalElement) {
    return {
      modal: modalElement,
      form: document.getElementById("inviteUserForm"),
      sectionGroup: document.getElementById("sectionAssignmentGroup"),
      sectionIdField: document.getElementById("inviteSectionId"),
      roleSelect: document.getElementById("inviteRole"),
      firstNameField: document.getElementById("inviteFirstName"),
      lastNameField: document.getElementById("inviteLastName"),
      programSelection: document.getElementById("programSelection"),
      inviteProgramsSelect: document.getElementById("invitePrograms"),
      options,
    };
  }

  function openInviteModal(options = {}) {
    const modalElement = document.getElementById("inviteUserModal");
    if (!modalElement) {
      console.warn("Invite modal is not present in the current DOM.");
      return;
    }
    const workflowName = options.workflow || DEFAULT_INVITE_WORKFLOW;
    const workflow = getInviteModalWorkflow(workflowName);
    const context = buildInviteModalContext(options, modalElement);
    workflow.reset(context);
    workflow.setup(context);
    new bootstrap.Modal(modalElement).show();
  }

  async function handleInviteUser(event, deps) {
    event.preventDefault();
    const {
      hasInvitationsView,
      loadInvitations,
      setButtonLoadingState,
      showError,
      showSuccess,
      showWarning,
    } = deps;
    const form = event.target;
    const formData = new FormData(form);
    const submitBtn = document.getElementById("sendInviteBtn");

    if (!form.checkValidity()) {
      form.classList.add("was-validated");
      return;
    }

    setButtonLoadingState(submitBtn, true);

    try {
      const response = await fetch("/api/auth/invite", {
        method: "POST",
        headers: getCsrfHeaders(),
        body: JSON.stringify(buildInvitationPayload(formData)),
      });
      const result = await response.json();

      if (!response.ok || !result.success) {
        throw new Error(result.error || "Failed to send invitation");
      }

      const successMessage = result.message || "Invitation sent successfully!";
      displayInvitationResult(
        successMessage,
        result.email_error,
        showWarning,
        showSuccess,
      );
      bootstrap.Modal.getInstance(
        document.getElementById("inviteUserModal"),
      ).hide();
      if (hasInvitationsView()) {
        loadInvitations();
      }
      document.dispatchEvent(new CustomEvent("faculty-invited"));
    } catch (error) {
      console.error("Error sending invitation:", error);
      showError("Failed to send invitation: " + error.message);
    } finally {
      setButtonLoadingState(submitBtn, false);
    }
  }

  function registerDefaultInviteWorkflows() {
    registerInviteModalWorkflow(DEFAULT_INVITE_WORKFLOW, {
      reset({ form, sectionGroup, sectionIdField, roleSelect }) {
        if (form) {
          form.reset();
          form.classList.remove("was-validated");
        }
        if (sectionGroup) {
          sectionGroup.style.display = "none";
        }
        if (sectionIdField) {
          sectionIdField.value = "";
        }
        if (roleSelect) {
          roleSelect.value = "instructor";
          setProgramSelectionVisibility("instructor");
        }
      },
      setup({
        options = {},
        sectionGroup,
        sectionIdField,
        roleSelect,
        inviteProgramsSelect,
        firstNameField,
        lastNameField,
      }) {
        const hasSection = Boolean(options.sectionId);
        if (hasSection && sectionGroup) {
          sectionGroup.style.display = "block";
          if (sectionIdField) {
            sectionIdField.value = options.sectionId;
          }
        }

        const roleToApply =
          options.prefillRole ||
          (hasSection ? "instructor" : roleSelect?.value) ||
          "instructor";
        if (roleSelect) {
          roleSelect.value = roleToApply;
        }
        setProgramSelectionVisibility(roleToApply);

        if (firstNameField) {
          firstNameField.value = options.firstName || "";
        }
        if (lastNameField) {
          lastNameField.value = options.lastName || "";
        }

        if (
          options.programId &&
          roleToApply === "program_admin" &&
          inviteProgramsSelect
        ) {
          const applySelection = () => {
            Array.from(inviteProgramsSelect.options).forEach((opt) => {
              opt.selected = opt.value === options.programId;
            });
          };
          if (inviteProgramsSelect.options.length === 0) {
            setTimeout(applySelection, 50);
          } else {
            applySelection();
          }
        }
      },
    });

    registerInviteModalWorkflow("sectionAssignment", {
      reset: getInviteModalWorkflow(DEFAULT_INVITE_WORKFLOW).reset,
      setup(context) {
        getInviteModalWorkflow(DEFAULT_INVITE_WORKFLOW).setup(context);
        if (context.modal) {
          context.modal.dataset.workflow = "sectionAssignment";
        }
      },
    });
  }

  const exportsObj = {
    DEFAULT_INVITE_WORKFLOW,
    INVITATION_EMAIL_FAILED_MESSAGE,
    displayInvitationResult,
    getInviteModalWorkflow,
    getInviteModalWorkflowNames,
    handleInviteUser,
    handleRoleSelectionChange,
    isInvitationDeliveryFailedMessage,
    loadPrograms,
    openInviteModal,
    registerDefaultInviteWorkflows,
    registerInviteModalWorkflow,
    resetInviteModalWorkflows,
    setProgramSelectionVisibility,
  };

  if (typeof globalThis !== "undefined") {
    globalThis.AdminInvites = exportsObj;
  }
  if (typeof module !== "undefined" && module.exports) {
    module.exports = exportsObj;
  }
})();
