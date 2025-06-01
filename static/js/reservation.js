document.addEventListener("DOMContentLoaded", () => {
    function setupDropdown(selectId, dropdownId) {
        const originalSelect = document.querySelector(`#${selectId}`);
        const customDropdown = document.getElementById(dropdownId);
        const optionsData = Array.from(originalSelect.options)
            .filter(opt => opt.value || !opt.disabled)
            .map(opt => ({
                value: opt.value,
                label: opt.textContent.trim(),
                disabled: opt.disabled
            }));

        let currentValue = originalSelect.value || "";
        let currentLabel = optionsData.find(opt => opt.value === currentValue)?.label ||
                           optionsData.find(opt => !opt.disabled)?.label ||
                           "No options available";

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

    // 顯示原生 date picker
    const dateInput = document.getElementById("date");
    dateInput.addEventListener("click", () => {
        dateInput.showPicker?.();
    });

    // 🔁 當分店、日期、來賓數量改變時，重新抓取 time slots 並更新 dropdown
    function fetchTimeSlots() {
        const date = document.getElementById("date").value;
        const branch = document.getElementById("branch").value;
        const guests = document.getElementById("guests").value;

        if (!date || !branch) return;

        fetch(`/reservation/?date=${date}&branch=${branch}&guests=${guests}`)
            .then(response => response.text())
            .then(html => {
                const parser = new DOMParser();
                const doc = parser.parseFromString(html, 'text/html');

                const newSelect = doc.querySelector('#time_slot');
                if (!newSelect) return;

                const originalSelect = document.getElementById('time_slot');
                originalSelect.innerHTML = newSelect.innerHTML;

                // 更新 dropdown 資料與樣式
                setupDropdown("time_slot", "timeSlotDropdown");
            })
            .catch(err => console.error('Error fetching time slots:', err));
    }

    // 監聽變動事件
    document.getElementById("date").addEventListener("change", fetchTimeSlots);
    document.getElementById("branch").addEventListener("change", fetchTimeSlots);
    document.getElementById("guests").addEventListener("change", fetchTimeSlots);
});
