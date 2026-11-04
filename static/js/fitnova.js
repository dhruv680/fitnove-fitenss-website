/* FitNova Frontend JavaScript */

document.addEventListener('DOMContentLoaded', function () {
  // 1. Initialize Lucide Icons
  if (typeof lucide !== 'undefined') {
    lucide.createIcons();
  }

  // 2. Sidebar Collapsible State
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
      setTimeout(() => {
        if (typeof lucide !== 'undefined') {
          lucide.createIcons();
        }
      }, 250);
    });
  }

  // Close mobile sidebar on clicking outside
  document.addEventListener('click', function (e) {
    if (window.innerWidth < 992 && document.body.classList.contains('sidebar-open')) {
      const sidebar = document.querySelector('.fn-sidebar');
      const toggle = document.getElementById('fnSidebarToggle');
      if (sidebar && !sidebar.contains(e.target) && toggle && !toggle.contains(e.target)) {
        document.body.classList.remove('sidebar-open');
      }
    }
  });

  // 3. Hotkey: Press '/' to focus global search
  document.addEventListener('keydown', function (e) {
    if (e.key === '/' && document.activeElement.tagName !== 'INPUT' && document.activeElement.tagName !== 'TEXTAREA') {
      const searchInput = document.getElementById('fnGlobalSearchInput');
      if (searchInput) {
        e.preventDefault();
        searchInput.focus();
      }
    }
  });

  // 4. Form Submit Loading States (prevent duplicate submissions)
  const forms = document.querySelectorAll('form:not(.no-disable)');
  forms.forEach(form => {
    form.addEventListener('submit', function () {
      const submitBtn = form.querySelector('button[type="submit"]');
      if (submitBtn && !form.dataset.submitting) {
        form.dataset.submitting = 'true';
        const originalContent = submitBtn.innerHTML;
        submitBtn.disabled = true;
        submitBtn.innerHTML = `<span class="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span> Processing...`;
        setTimeout(() => {
          submitBtn.disabled = false;
          submitBtn.innerHTML = originalContent;
          delete form.dataset.submitting;
        }, 8000);
      }
    });
  });

  // 5. Auto-dismiss alerts after 5 seconds
  const alerts = document.querySelectorAll('.alert.alert-dismissible');
  alerts.forEach(alert => {
    setTimeout(() => {
      const bsAlert = bootstrap.Alert.getOrCreateInstance(alert);
      if (bsAlert) {
        bsAlert.close();
      }
    }, 5000);
  });
});

