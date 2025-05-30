document.addEventListener("DOMContentLoaded", function () {
  const reorderBtn = document.getElementById("order-again-btn");
  const modal = document.getElementById("orderModal");
  const closeModal = document.getElementById("closeModal");
  const modalContent = document.getElementById("modalContent");
  const confirmForm = document.getElementById("confirmReorderForm");
  const csrfToken = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content');

  if (reorderBtn) {
    const checkCartUrl = reorderBtn.getAttribute("data-check-cart-url");
    const reorderUrl = reorderBtn.getAttribute("data-reorder-url");

    if (!checkCartUrl || checkCartUrl === "null") {
      alert("Configuration error: Unable to check cart status. Please contact support.");
      return;
    }
    if (!reorderUrl || reorderUrl === "null") {
      alert("Configuration error: Unable to reorder. Please contact support.");
      return;
    }

    reorderBtn.addEventListener("click", function () {
      fetch(checkCartUrl, {
        method: "GET",
        headers: {
          "X-Requested-With": "XMLHttpRequest",
          "X-CSRFToken": csrfToken,
        },
      })
        .then(response => {
          if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
          return response.json();
        })
        .then(data => {
          if (data.is_empty) {
            window.location.href = reorderUrl;
          } else {
            modal.style.display = "flex";
          }
        })
        .catch(error => {
          alert("An error occurred while checking the cart. Please try again.");
        });
    });
  }

  closeModal.addEventListener("click", () => modal.style.display = "none");

  modal.addEventListener("click", function (event) {
    if (!modalContent.contains(event.target)) {
      modal.style.display = "none";
    }
  });

  if (confirmForm) {
    confirmForm.addEventListener("submit", function (e) {
      e.preventDefault();
      HTMLFormElement.prototype.submit.call(confirmForm);
    });
  }
});