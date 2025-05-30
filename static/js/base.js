// 控制手機右上選單開關
document.getElementById('menuToggle').addEventListener('click', () => {
  document.getElementById('mobileMenu').classList.remove('d-none');
});
document.getElementById('menuClose').addEventListener('click', () => {
  document.getElementById('mobileMenu').classList.add('d-none');
});

document.addEventListener("DOMContentLoaded", function () {
  const logoutBtns = [document.getElementById("logoutBtn"), document.getElementById("logoutBtnMobile")];
  const modal = document.getElementById("logoutModal");
  const closeBtn = document.getElementById("closeLogoutModal");
  const confirmBtn = document.getElementById("confirmLogout");

  logoutBtns.forEach(btn => {
    if (btn) {
      btn.addEventListener("click", () => {
        modal.classList.remove("d-none");
      });
    }
  });

  // 關閉 modal（叉叉或點外面）
  closeBtn.addEventListener("click", () => modal.classList.add("d-none"));
window.addEventListener("click", e => {
  if (e.target.id === "logoutModal") {
    modal.classList.add("d-none");
  }
});

  // 確認登出
  confirmBtn.addEventListener("click", () => {
    window.location.href = window.logoutUrl;
  });
});

function toggleDropdown(event) {
  event.stopPropagation();  
  const menu = document.getElementById('historyMenu');
  if (menu.style.display === 'block') {
    menu.style.display = 'none';
  } else {
    menu.style.display = 'block';
  }
}

document.addEventListener('click', function(event) {
  const menu = document.getElementById('historyMenu');
  if (menu) {
    menu.style.display = 'none';
  }
});