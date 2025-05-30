document.addEventListener("DOMContentLoaded", () => {
    function setupDropdown(selectId, dropdownId) {
    const originalSelect = document.querySelector(`#${selectId}`);
    const customDropdown = document.getElementById(dropdownId);
    const dateInput = document.getElementById("date");

    dateInput.addEventListener("click", () => {
        dateInput.showPicker?.(); 
    });

    const optionsData = Array.from(originalSelect.options)
        .filter(opt => opt.value || !opt.disabled) 
        .map(opt => ({
        value: opt.value,
        label: opt.textContent.trim(),
        disabled: opt.disabled
        }));

    let currentValue = originalSelect.value || "";
    let currentLabel = optionsData.find(opt => opt.value === currentValue)?.label || 
                        optionsData.find(opt => !opt.disabled)?.label || "No options available";

    if (!currentValue || !optionsData.find(opt => opt.value === currentValue && !opt.disabled)) {
        const firstValidOption = optionsData.find(opt => !opt.disabled);
        if (firstValidOption) {
        currentValue = firstValidOption.value;
        currentLabel = firstValidOption.label;
        originalSelect.value = currentValue;
        }
    }

    function createDropdown() {
        customDropdown.innerHTML = `
        <div class="selected">
            <span id="selectedText-${selectId}">${currentLabel}</span>
            <span class="arrow">ᐯ</span>
        </div>
        <div class="options"></div>
        `;

        const selected = customDropdown.querySelector(".selected");
        const optionsContainer = customDropdown.querySelector(".options");
        const selectedText = customDropdown.querySelector(`#selectedText-${selectId}`);

        optionsData.forEach(option => {
        const optDiv = document.createElement("div");
        optDiv.classList.add("option");
        if (option.disabled) {
            optDiv.classList.add("disabled");
        }
        optDiv.textContent = option.label;
        optDiv.dataset.value = option.value;

        if (!option.disabled) {
            optDiv.addEventListener("click", () => {
            currentValue = option.value;
            selectedText.textContent = option.label;
            optionsContainer.style.display = "none";
            customDropdown.classList.remove("active"); 
            originalSelect.value = option.value;
            originalSelect.dispatchEvent(new Event("change"));
            });
        }

        optionsContainer.appendChild(optDiv);
        });

        selected.addEventListener("click", (e) => {
        e.stopPropagation();
        const isOpen = optionsContainer.style.display === "block";
        document.querySelectorAll(".dropdown .options").forEach(opt => opt.style.display = "none");
        document.querySelectorAll(".dropdown").forEach(dropdown => dropdown.classList.remove("active"));
        optionsContainer.style.display = isOpen ? "none" : "block";
        customDropdown.classList.toggle("active", !isOpen); 
        });

        document.addEventListener("click", (e) => {
        if (!customDropdown.contains(e.target)) {
            optionsContainer.style.display = "none";
            customDropdown.classList.remove("active");
        }
        });
    }

    createDropdown();
    }

    setupDropdown("guests", "guestsDropdown");
    setupDropdown("branch", "branchDropdown");
    setupDropdown("time_slot", "timeSlotDropdown");
});