document.addEventListener("DOMContentLoaded", () => {
    const branchSelect = document.querySelector("#id_pickup_branch");
    const timeSlotSelect = document.querySelector("#id_time_slot");
    const customDropdownPickup = document.getElementById("customDropdown") || document.getElementById("customDropdownPickupUnauth");
    const customDropdownTimeSlot = document.getElementById("customDropdownTimeSlot") || document.getElementById("customDropdownTimeSlotUnauth");

    const pickupOptionsData = Array.from(branchSelect.options)
        .filter(opt => opt.value)
        .map(opt => ({
            value: opt.value,
            label: opt.textContent.trim()
        }));
    let currentPickupValue = branchSelect.value || "";
    let currentPickupLabel = pickupOptionsData.find(opt => opt.value === currentPickupValue)?.label || "Select a pickup location";

    function createDropdown(selectElement, customDropdown, optionsData, defaultLabel, selectedTextId) {
        let currentValue = selectElement.value || "";
        let currentLabel = optionsData.find(opt => opt.value === currentValue)?.label || defaultLabel;

        customDropdown.innerHTML = `
            <div class="selected">
                <span id="${selectedTextId}">${currentLabel}</span>
                <span class="arrow">ᐯ</span>
            </div>
            <div class="options"></div>
        `;

        const selected = customDropdown.querySelector(".selected");
        const optionsContainer = customDropdown.querySelector(".options");
        const selectedText = customDropdown.querySelector(`#${selectedTextId}`);

        optionsContainer.innerHTML = '';

        if (optionsData.length === 0) {
            const noOptionDiv = document.createElement("div");
            noOptionDiv.classList.add("option", "disabled");
            noOptionDiv.textContent = "No available time slots";
            optionsContainer.appendChild(noOptionDiv);
        } else {
            optionsData.forEach(option => {
                const optDiv = document.createElement("div");
                optDiv.classList.add("option");
                optDiv.textContent = option.label;
                optDiv.dataset.value = option.value;

                optDiv.addEventListener("click", (e) => {
                    e.stopPropagation(); 
                    currentValue = option.value;
                    selectedText.textContent = option.label;
                    optionsContainer.style.display = "none";
                    customDropdown.classList.remove("active");
                    selectElement.value = option.value;
                    selectElement.dispatchEvent(new Event("change"));
                });

                optionsContainer.appendChild(optDiv);
            });
        }

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

    function fetchTimeSlots(branchId) {
        fetch(`/get_available_order_slots/?branch_id=${branchId}`)
            .then(response => response.json())
            .then(data => {
                let options = [];
                if (data.error || !data.options || data.options.length === 0) {
                    console.warn("No time slots available:", data.error || "No options returned");
                    options = [{ value: "", label: "No available time slots" }];
                } else {
                    options = data.options;
                }

                timeSlotSelect.innerHTML = "";
                options.forEach(option => {
                    const opt = document.createElement("option");
                    opt.value = option.value;
                    opt.textContent = option.label;
                    timeSlotSelect.appendChild(opt);
                });

                createDropdown(timeSlotSelect, customDropdownTimeSlot, options, "Select a pickup time slot", "selectedTextTimeSlot");
            })
            .catch(error => {
                console.error("Error fetching time slots:", error);
            });
    }

    createDropdown(branchSelect, customDropdownPickup, pickupOptionsData, "Select a pickup location", "selectedTextPickup");

    if (branchSelect.value) {
        fetchTimeSlots(branchSelect.value);
    }

    branchSelect.addEventListener("change", () => {
        fetchTimeSlots(branchSelect.value);
    });
});