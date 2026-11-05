/* ==========================================================================
   FitNova – Advanced Interactive Animation & UI Engine
   ========================================================================== */

document.addEventListener('DOMContentLoaded', function () {
  // 1. Initialize Lucide Icons
  initLucide();

  // 2. Animated Numerical Counters (Count Up)
  initAnimatedCounters();

  // 3. Collapsible Sidebar Engine
  initSidebar();

  // 4. Global Search Hotkey ('/')
  initSearchHotkey();

  // 5. Button Ripple Click Effect
  initButtonRipples();

  // 6. Form Validation Feedback & Loading Prevention
  initFormInteractions();

  // 7. Auto-Dismiss and Slide Toasts
  initToasts();
});

/* --------------------------------------------------------------------------
   1. Lucide Icons Helper
   -------------------------------------------------------------------------- */
function initLucide() {
  if (typeof lucide !== 'undefined') {
    lucide.createIcons();
  }
}

/* --------------------------------------------------------------------------
   2. Number Count-Up Animation Engine
   -------------------------------------------------------------------------- */
function initAnimatedCounters() {
  const counterElements = document.querySelectorAll('.fn-counter, .fn-stat-value');

  counterElements.forEach(el => {
    // If element has text that contains numbers
    const rawText = el.innerText.trim();
    if (!rawText || el.dataset.animated) return;

    // Detect prefix (e.g. '$', '+'), number, and suffix (e.g. '%', '/mo')
    const match = rawText.match(/^([^0-9]*)([\d,]+(?:\.\d+)?)(.*)$/);
    if (!match) return;

    const prefix = match[1] || '';
    const numericStr = match[2].replace(/,/g, '');
    const suffix = match[3] || '';
    const targetValue = parseFloat(numericStr);

    if (isNaN(targetValue)) return;

    const hasDecimals = numericStr.includes('.');
    const decimalPlaces = hasDecimals ? numericStr.split('.')[1].length : 0;
    const duration = 1200; // ms
    const startTime = performance.now();

    el.dataset.animated = 'true';
    el.style.opacity = '1';

    function easeOutQuart(x) {
      return 1 - Math.pow(1 - x, 4);
    }

    function updateCounter(currentTime) {
      const elapsed = currentTime - startTime;
      const progress = Math.min(elapsed / duration, 1);
      const easedProgress = easeOutQuart(progress);
      const currentValue = targetValue * easedProgress;

      // Format with commas
      let formattedNumber = hasDecimals 
        ? currentValue.toFixed(decimalPlaces) 
        : Math.round(currentValue).toLocaleString('en-US');

      el.innerText = `${prefix}${formattedNumber}${suffix}`;

      if (progress < 1) {
        requestAnimationFrame(updateCounter);
      } else {
        // Guarantee final exact text
        el.innerText = rawText;
      }
    }

    requestAnimationFrame(updateCounter);
  });
}

/* --------------------------------------------------------------------------
   3. Collapsible Sidebar Engine with LocalStorage Memory
   -------------------------------------------------------------------------- */
function initSidebar() {
  const sidebarToggleBtn = document.getElementById('fnSidebarToggle');
  const savedState = localStorage.getItem('fitnova_sidebar_collapsed');

  if (savedState === 'true' && window.innerWidth >= 992) {
    document.body.classList.add('sidebar-collapsed');
  }

  if (sidebarToggleBtn) {
    sidebarToggleBtn.addEventListener('click', function () {
      if (window.innerWidth < 992) {
        document.body.classList.toggle('sidebar-open');
      } else {
        document.body.classList.toggle('sidebar-collapsed');
        const isCollapsed = document.body.classList.contains('sidebar-collapsed');
        localStorage.setItem('fitnova_sidebar_collapsed', isCollapsed);
      }
      setTimeout(initLucide, 250);
    });
  }

  // Close mobile sidebar on backdrop click
  document.addEventListener('click', function (e) {
    if (window.innerWidth < 992 && document.body.classList.contains('sidebar-open')) {
      const sidebar = document.querySelector('.fn-sidebar');
      const toggle = document.getElementById('fnSidebarToggle');
      if (sidebar && !sidebar.contains(e.target) && toggle && !toggle.contains(e.target)) {
        document.body.classList.remove('sidebar-open');
      }
    }
  });
}

/* --------------------------------------------------------------------------
   4. Global Search Keyboard Shortcut ('/')
   -------------------------------------------------------------------------- */
function initSearchHotkey() {
  document.addEventListener('keydown', function (e) {
    if (e.key === '/' && document.activeElement.tagName !== 'INPUT' && document.activeElement.tagName !== 'TEXTAREA') {
      const searchInput = document.getElementById('fnGlobalSearchInput');
      if (searchInput) {
        e.preventDefault();
        searchInput.focus();
        searchInput.parentElement.style.transform = 'scale(1.02)';
        setTimeout(() => {
          searchInput.parentElement.style.transform = '';
        }, 200);
      }
    }
  });
}

/* --------------------------------------------------------------------------
   5. Button Ripple Click Effect
   -------------------------------------------------------------------------- */
function initButtonRipples() {
  const buttons = document.querySelectorAll('.btn-fn-accent, .btn-fn-primary');
  buttons.forEach(btn => {
    btn.addEventListener('click', function (e) {
      const rect = btn.getBoundingClientRect();
      const circle = document.createElement('span');
      const diameter = Math.max(rect.width, rect.height);
      const radius = diameter / 2;

      circle.style.width = circle.style.height = `${diameter}px`;
      circle.style.left = `${e.clientX - rect.left - radius}px`;
      circle.style.top = `${e.clientY - rect.top - radius}px`;
      circle.style.position = 'absolute';
      circle.style.borderRadius = '50%';
      circle.style.background = 'rgba(255, 255, 255, 0.35)';
      circle.style.pointerEvents = 'none';
      circle.style.transform = 'scale(0)';
      circle.style.animation = 'fnRipple 0.5s ease-out';

      btn.appendChild(circle);
      setTimeout(() => circle.remove(), 500);
    });
  });
}

// Inject keyframe for ripple dynamically if not in css
if (!document.getElementById('fn-ripple-keyframes')) {
  const style = document.createElement('style');
  style.id = 'fn-ripple-keyframes';
  style.innerHTML = `@keyframes fnRipple { to { transform: scale(3.5); opacity: 0; } }`;
  document.head.appendChild(style);
}

/* --------------------------------------------------------------------------
   6. Form Validation & Smooth Submit Feedback
   -------------------------------------------------------------------------- */
function initFormInteractions() {
  const forms = document.querySelectorAll('form:not(.no-disable)');
  forms.forEach(form => {
    form.addEventListener('submit', function (e) {
      // Check required fields
      let isValid = true;
      const requiredInputs = form.querySelectorAll('input[required], select[required], textarea[required]');
      requiredInputs.forEach(input => {
        if (!input.value.trim()) {
          isValid = false;
          input.classList.add('is-invalid');
          setTimeout(() => input.classList.remove('is-invalid'), 600);
        }
      });

      if (!isValid) {
        e.preventDefault();
        return;
      }

      // Show spinner on valid submission
      const submitBtn = form.querySelector('button[type="submit"]');
      if (submitBtn && !form.dataset.submitting) {
        form.dataset.submitting = 'true';
        const originalWidth = submitBtn.offsetWidth;
        const originalContent = submitBtn.innerHTML;
        submitBtn.style.minWidth = `${originalWidth}px`;
        submitBtn.disabled = true;
        submitBtn.innerHTML = `<span class="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span> Saving...`;

        setTimeout(() => {
          submitBtn.disabled = false;
          submitBtn.innerHTML = originalContent;
          delete form.dataset.submitting;
        }, 8000);
      }
    });
  });
}

/* --------------------------------------------------------------------------
   7. Modern Toast Notifications with Auto-Dismiss Progress
   -------------------------------------------------------------------------- */
function initToasts() {
  const alerts = document.querySelectorAll('.alert.alert-dismissible');
  alerts.forEach(alert => {
    alert.classList.add('fn-animate-in');
    setTimeout(() => {
      if (typeof bootstrap !== 'undefined' && bootstrap.Alert) {
        const bsAlert = bootstrap.Alert.getOrCreateInstance(alert);
        if (bsAlert) bsAlert.close();
      }
    }, 5500);
  });
}

/* Expose global helper for dynamic toast creation */
window.showFitNovaToast = function (message, type = 'success') {
  let container = document.querySelector('.fn-toast-container');
  if (!container) {
    container = document.createElement('div');
    container.className = 'fn-toast-container';
    document.body.appendChild(container);
  }

  const toast = document.createElement('div');
  toast.className = 'fn-toast';
  const icon = type === 'success' ? 'check-circle' : (type === 'danger' || type === 'error' ? 'alert-circle' : 'info');
  const iconColor = type === 'success' ? 'text-success' : (type === 'danger' || type === 'error' ? 'text-danger' : 'text-primary');

  toast.innerHTML = `
    <i data-lucide="${icon}" class="${iconColor}" style="width: 20px; height: 20px; flex-shrink: 0; margin-top: 2px;"></i>
    <div class="flex-grow-1 small fw-semibold text-dark">${message}</div>
    <button type="button" class="btn-close" style="font-size: 0.75rem;" onclick="this.parentElement.remove()"></button>
    <div class="fn-toast-progress"></div>
  `;

  container.appendChild(toast);
  initLucide();

  setTimeout(() => {
    toast.style.transition = 'all 0.35s ease';
    toast.style.opacity = '0';
    toast.style.transform = 'translateX(50px)';
    setTimeout(() => toast.remove(), 350);
  }, 4500);
};
