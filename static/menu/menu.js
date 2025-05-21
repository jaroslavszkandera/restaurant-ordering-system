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

  if ((direction < 0 && scrollIndex <= 0) || (direction > 0 && scrollIndex >= maxScrollIndex)) {
    return;
  }

  scrollIndex = Math.max(0, Math.min(scrollIndex + direction, maxScrollIndex));
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

  console.log({
    scrollIndex,
    scrollOffset,
    avgBtnWidth,
    visibleCount,
    maxScrollIndex,
    wrapperWidth: wrapper.offsetWidth,
    listWidth: list.scrollWidth
  });
};

// Fit text to container width (single line, shrink if too long)
function fitTextToWidth(el, maxFontSize = 1.2, minFontSize = 0.6) {
  if (!el || !el.parentElement) {
    console.warn('Invalid element or parent in fitTextToWidth:', el);
    return maxFontSize;
  }

  const parent = el.parentElement;
  const style = window.getComputedStyle(parent);
  const paddingLeft = parseFloat(style.paddingLeft) || 0;
  const paddingRight = parseFloat(style.paddingRight) || 0;
  const parentWidth = parent.clientWidth - paddingLeft - paddingRight;

  if (parentWidth <= 0) {
    console.warn('Parent width is invalid:', parentWidth, parent);
    return maxFontSize;
  }

  // Save original styles
  const originalFontSize = el.style.fontSize;
  const originalWhiteSpace = el.style.whiteSpace;

  // Temporarily disable overflow/ellipsis during measurement
  const originalOverflow = el.style.overflow;
  const originalTextOverflow = el.style.textOverflow;

  el.style.whiteSpace = 'nowrap';
  el.style.overflow = 'visible';
  el.style.textOverflow = 'clip';

  let fontSize = maxFontSize;
  let low = minFontSize;
  let high = maxFontSize;
  let iterations = 0;
  const maxIterations = 50;

  while (low <= high && iterations < maxIterations) {
    fontSize = (low + high) / 2;
    el.style.fontSize = `${fontSize}rem`;
    el.offsetWidth; // force reflow

    const scrollWidth = el.scrollWidth;

    if (scrollWidth <= parentWidth) {
      low = fontSize + 0.005;
    } else {
      high = fontSize - 0.005;
    }

    iterations++;
  }

  // Apply final font size
  fontSize = Math.max(minFontSize, Math.min(maxFontSize, fontSize));
  el.style.fontSize = `${fontSize}rem`;

  // Restore overflow styles (but still no ellipsis!)
  el.style.whiteSpace = originalWhiteSpace || '';
  el.style.overflow = 'visible';
  el.style.textOverflow = 'clip';

  return fontSize;
}


// Adjust card content (font size and image height)
function adjustCardContent() {
  const cards = document.querySelectorAll('.menu-card');
  if (!cards.length) {
    console.warn('No menu cards found');
    return;
  }

  cards.forEach(card => {
    const title = card.querySelector('.card-left h5');
    const img = card.querySelector('.card-left img');

    if (!title) {
      console.warn('Missing title in card:', card);
      return;
    }
    // Image is optional due to fa-utensils fallback
    if (!img) {
      console.warn('No image in card, using icon:', card);
    }

    const fontSize = fitTextToWidth(title);
    if (!fontSize || fontSize <= 0) {
      console.error('Invalid font size returned:', fontSize);
      return;
    }

    const maxTextHeight = fontSize * 1.2; // Line-height in rem
    const cardHeight = card.clientHeight;
    const gapBetweenImgAndTitle = 5;

    const cardLeft = card.querySelector('.card-left');
    const style = window.getComputedStyle(cardLeft);
    const paddingTop = parseFloat(style.paddingTop) || 0;
    const paddingBottom = parseFloat(style.paddingBottom) || 0;

    // Only adjust image if present
    if (img) {
      const availableHeight = (cardHeight / 2) - maxTextHeight - gapBetweenImgAndTitle - paddingTop - paddingBottom;
      const maxImgHeight = Math.max(availableHeight, 0);
      img.style.maxHeight = `${maxImgHeight}px`;
      img.style.marginBottom = `${gapBetweenImgAndTitle}px`;
    }

    console.log({
      cardId: card.id || 'unnamed',
      cardHeight,
      fontSize,
      maxTextHeight,
      paddingTop,
      paddingBottom,
      availableHeight: img ? (cardHeight / 2) - maxTextHeight - gapBetweenImgAndTitle - paddingTop - paddingBottom : 'N/A',
      maxImgHeight: img ? Math.max(availableHeight, 0) : 'N/A'
    });
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

// Run adjustCardContent on initial load
window.addEventListener('load', adjustCardContent);

// Run adjustCardContent on window resize with debounce
window.addEventListener('resize', debounce(adjustCardContent, 100));

// Run adjustCardContent after DOM content is loaded to catch early renders
document.addEventListener('DOMContentLoaded', adjustCardContent);