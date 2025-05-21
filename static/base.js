// 控制手機右上選單開關
document.getElementById('menuToggle').addEventListener('click', () => {
  document.getElementById('mobileMenu').classList.remove('d-none');
});
document.getElementById('menuClose').addEventListener('click', () => {
  document.getElementById('mobileMenu').classList.add('d-none');
});