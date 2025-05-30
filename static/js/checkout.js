document.addEventListener("DOMContentLoaded", () => {
  const originalSelect = document.querySelector(".dropdown-original");
  const customDropdown = document.getElementById("customDropdown");

  const optionsData = Array.from(originalSelect.options)
    .filter(opt => opt.value)  
    .map(opt => ({
      value: opt.value,
      label: opt.textContent.trim()
    }));

  let currentValue = originalSelect.value || "";
  let currentLabel = optionsData.find(opt => opt.value === currentValue)?.label || "Select a pickup location";

  function createDropdown() {
    customDropdown.innerHTML = `
      <div class="selected">
        <span id="selectedText">${currentLabel}</span>
        <span class="arrow">ᐯ</span>
      </div>
      <div class="options"></div>
    `;

    const selected = customDropdown.querySelector(".selected");
    const optionsContainer = customDropdown.querySelector(".options");
    const selectedText = customDropdown.querySelector("#selectedText");

    optionsData.forEach(option => {
      const optDiv = document.createElement("div");
      optDiv.classList.add("option");
      optDiv.textContent = option.label;
      optDiv.dataset.value = option.value;

      optDiv.addEventListener("click", () => {
        currentValue = option.value;
        selectedText.textContent = option.label;
        optionsContainer.style.display = "none";

        originalSelect.value = option.value;
        originalSelect.dispatchEvent(new Event("change"));
      });

      optionsContainer.appendChild(optDiv);
    });

    selected.addEventListener("click", (e) => {
      e.stopPropagation();
      const isOpen = optionsContainer.style.display === "block";

      document.querySelectorAll(".dropdown .options").forEach(opt => opt.style.display = "none");
      optionsContainer.style.display = isOpen ? "none" : "block";
    });

    // 點擊頁面其他地方關閉下拉選單
    document.addEventListener("click", (e) => {
      if (!customDropdown.contains(e.target)) {
        optionsContainer.style.display = "none";
      }
    });
  }

  createDropdown();
});