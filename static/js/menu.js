$(document).ready(function () {
  // Add-to-cart form submission
  $('.add-to-cart-form').on('submit', function (e) {
    e.preventDefault();
    let form = $(this);
    let url = form.attr('action');
    let button = form.find('.btn');
    let originalText = button.text();
    button.prop('disabled', true).text('...');

    $.ajax({
      type: 'POST',
      url: url,
      data: form.serialize(),
      success: function (data) {
        if (data.status === 'success') {
          Swal.fire({
            toast: true,
            icon: 'success',
            title: data.message || 'Item added!',
            position: 'top-end',
            showConfirmButton: false,
            timer: 2000
          });
          if (data.cart_total_quantity !== undefined) {
            $('.cart-count').text(data.cart_total_quantity);
          }
          form.find('input[type="number"]').val(1);
        } else {
          Swal.fire({
            toast: true,
            icon: 'error',
            title: 'Error',
            html: data.message || 'An error occurred.',
            position: 'top-end',
            showConfirmButton: false,
            timer: 3000
          });
        }
      },
      error: function () {
        Swal.fire({
          toast: true,
          icon: 'error',
          title: 'Oops...',
          text: 'Something went wrong. Try again.',
          position: 'top-end',
          showConfirmButton: false,
          timer: 3000
        });
      },
      complete: function () {
        button.prop('disabled', false).text(originalText);
      }
    });
  });

  // Category button clicks
  $('.category-list').on('click', '.category-btn', function (e) {
    e.preventDefault();
    let $btn = $(this);
    let url = $btn.data('href');

    $('.category-btn').removeClass('active');
    $btn.addClass('active');

    $.ajax({
      url: url,
      type: 'GET',
      success: function (data) {
        $('#menu-items').html($(data).find('#menu-items').html());
        // Re-bind add-to-cart forms
        $('.add-to-cart-form').off('submit').on('submit', function (e) {
          e.preventDefault();
          let form = $(this);
          let url = form.attr('action');
          let button = form.find('.btn');
          let originalText = button.text();
          button.prop('disabled', true).text('...');

          $.ajax({
            type: 'POST',
            url: url,
            data: form.serialize(),
            success: function (data) {
              if (data.status === 'success') {
                Swal.fire({
                  toast: true,
                  icon: 'success',
                  title: data.message || 'Item added!',
                  position: 'top-end',
                  showConfirmButton: false,
                  timer: 2000
                });
                if (data.cart_total_quantity !== undefined) {
                  $('.cart-count').text(data.cart_total_quantity);
                }
                form.find('input[type="number"]').val(1);
              } else {
                Swal.fire({
                  toast: true,
                  icon: 'error',
                  title: 'Error',
                  html: data.message || 'An error occurred.',
                  position: 'top-end',
                  showConfirmButton: false,
                  timer: 3000
                });
              }
            },
            error: function () {
              Swal.fire({
                toast: true,
                icon: 'error',
                title: 'Oops...',
                text: 'Something went wrong. Try again.',
                position: 'top-end',
                showConfirmButton: false,
                timer: 3000
              });
            },
            complete: function () {
              button.prop('disabled', false).text(originalText);
            }
          });
        });
        // Adjust card content after menu items update
        adjustCardContent();
      },
      error: function () {
        Swal.fire({
          icon: 'error',
          title: 'Failed to load category',
          text: 'Please try again later.',
        });
      }
    });

  });

  // Floating category menu toggle
  $('#floating-menu-btn').on('click', function () {
    $('#floating-category-menu').toggleClass('show');
  });

  // Close floating menu when a category is clicked
  $('#floating-category-menu').on('click', 'a', function () {
    $('#floating-category-menu').removeClass('show');
  });
});

// 點擊選單外區域時關閉浮動選單
$(document).on('click', function (event) {
  const $menu = $('#floating-category-menu');
  const $toggleBtn = $('#floating-menu-btn');
  // 如果點擊的不是選單本身、也不是 toggle 按鈕，則關閉
  if (!$menu.is(event.target) && $menu.has(event.target).length === 0 &&
      !$toggleBtn.is(event.target) && $toggleBtn.has(event.target).length === 0) {
    $menu.removeClass('show');
  }
});

// Scroll functionality
window.scrollCategories = function(direction) {
  const wrapper = document.querySelector('.category-list-wrapper');
  const list = document.querySelector('.category-list');
  const btns = list ? list.querySelectorAll('.category-btn') : [];
  const leftBtn = document.querySelector('.scroll-btn.left');
  const rightBtn = document.querySelector('.scroll-btn.right');

  if (!wrapper || !list || btns.length === 0) {
    console.error('Missing elements:', { wrapper, list, btnCount: btns.length });
    return;
  }

  let scrollIndex = window.scrollIndex || 0;
  const btnWidths = Array.from(btns).map(btn => btn.offsetWidth);
  const avgBtnWidth = btnWidths.reduce((sum, w) => sum + w, 0) / btnWidths.length + 8;

  const visibleCount = Math.floor(wrapper.offsetWidth / avgBtnWidth);
  const maxScrollIndex = Math.max(0, btns.length - visibleCount);

  const isMobile = window.innerWidth <= 768; // 判斷裝置大小
  const scrollStep = isMobile ? 1 : 3;       // 手機滑1個、桌機滑2個

  if ((direction < 0 && scrollIndex <= 0) || (direction > 0 && scrollIndex >= maxScrollIndex)) {
    return;
  }

  scrollIndex = Math.max(0, Math.min(scrollIndex + direction * scrollStep, maxScrollIndex));
  const scrollOffset = scrollIndex * avgBtnWidth;

  wrapper.scrollTo({
    left: scrollOffset,
    behavior: 'smooth'
  });

  window.scrollIndex = scrollIndex;

  if (leftBtn) {
    leftBtn.classList.toggle('disabled', scrollIndex <= 0);
  }
  if (rightBtn) {
    rightBtn.classList.toggle('disabled', scrollIndex >= maxScrollIndex);
  }

  // optional debug:
  // console.log({ scrollIndex, scrollOffset, avgBtnWidth, visibleCount, maxScrollIndex });
};

// Fit text to container width (strictly two lines, shrink if needed)
function fitTextToWidth(el) {
  const maxHeight = el.clientHeight; // h5 已設定 height
  let fontSize = parseFloat(getComputedStyle(el).fontSize);
  const minFontSize = 12;
  const lineHeight = 1.2;

  el.style.whiteSpace = "normal";
  el.style.display = "flex";
  el.style.alignItems = "center";
  el.style.justifyContent = "center";
  el.style.textAlign = "center";

  while (el.scrollHeight > maxHeight && fontSize > minFontSize) {
    fontSize -= 1;
    el.style.fontSize = `${fontSize}px`;
    el.style.lineHeight = `${lineHeight}`;
  }

  return { fontSize };
}

// Adjust card content (font size, lines, and image dimensions)
function adjustCardContent() {
  const cards = document.querySelectorAll('.menu-card');
  if (!cards.length) return;

  cards.forEach(card => {
    const cardLeft = card.querySelector('.card-left');
    const title = cardLeft.querySelector('h5');
    const img = cardLeft.querySelector('img');

    if (!title || !img) return;

    // Apply font scaling
    const { fontSize } = fitTextToWidth(title);

    // 計算剩餘空間給圖片
    const cardLeftHeight = cardLeft.clientHeight;
    const gap = 5;
    const lineHeight = 1.2;
    const titleHeight = fontSize * lineHeight * 2;

    const maxImgHeight = cardLeftHeight - titleHeight - gap;
    img.style.height = `${maxImgHeight}px`;
    img.style.objectFit = 'cover';
    img.style.marginBottom = `${gap}px`;
  });
}

// Debounce function
function debounce(func, wait) {
  let timeout;
  return function (...args) {
    clearTimeout(timeout);
    timeout = setTimeout(() => func.apply(this, args), wait);
  };
}

document.addEventListener("DOMContentLoaded", () => {
  adjustCardContent();
});

window.addEventListener("load", () => {
  adjustCardContent();
});

window.addEventListener("resize", () => {
  adjustCardContent();
});

