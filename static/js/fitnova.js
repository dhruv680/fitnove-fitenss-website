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

  // 8. Bootstrap Tooltips Initializer
  initTooltips();

  // 9. Quick View Drawer Engine
  initMemberDrawer();
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
   8. Bootstrap Tooltips Initializer
   -------------------------------------------------------------------------- */
function initTooltips() {
  if (typeof bootstrap !== 'undefined' && bootstrap.Tooltip) {
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.forEach(function (tooltipTriggerEl) {
      new bootstrap.Tooltip(tooltipTriggerEl, {
        boundary: document.body,
        fallbackPlacements: ['top', 'bottom', 'right']
      });
    });
  }
}

/* --------------------------------------------------------------------------
   9. Slide-Over Quick View Drawer Engine
   -------------------------------------------------------------------------- */
function initMemberDrawer() {
  const backdrop = document.getElementById('fnMemberDrawerBackdrop');
  const drawer = document.getElementById('fnMemberDrawer');
  if (!drawer) return;

  // Global close drawer function
  window.closeMemberDrawer = function () {
    drawer.classList.remove('open');
    if (backdrop) backdrop.classList.remove('show');
    document.body.style.overflow = '';
    // Remove selected state from table rows
    document.querySelectorAll('.fn-table tbody tr.table-row-selected').forEach(tr => {
      tr.classList.remove('table-row-selected');
    });
  };

  // Close triggers
  if (backdrop) {
    backdrop.addEventListener('click', window.closeMemberDrawer);
  }

  const closeBtn = drawer.querySelector('.fn-drawer-close-btn');
  if (closeBtn) {
    closeBtn.addEventListener('click', window.closeMemberDrawer);
  }

  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape' && drawer.classList.contains('open')) {
      window.closeMemberDrawer();
    }
  });

  // Global open drawer function
  window.openMemberDrawer = function (memberId, triggerRow) {
    if (triggerRow) {
      document.querySelectorAll('.fn-table tbody tr').forEach(tr => tr.classList.remove('table-row-selected'));
      triggerRow.classList.add('table-row-selected');
    }

    if (backdrop) backdrop.classList.add('show');
    drawer.classList.add('open');
    document.body.style.overflow = 'hidden';

    // Show Loading Skeleton
    const drawerContent = document.getElementById('fnDrawerContent');
    if (drawerContent) {
      drawerContent.innerHTML = `
        <div class="py-5 text-center">
          <div class="spinner-border text-primary mb-3" style="width: 2.5rem; height: 2.5rem; color: #7657E8 !important;" role="status"></div>
          <div class="text-muted small fw-semibold">Loading athlete profile & history...</div>
        </div>
      `;
    }

    // Fetch member JSON
    fetch(`/members/${memberId}/quick-view/`)
      .then(res => {
        if (!res.ok) throw new Error('Could not load member details');
        return res.json();
      })
      .then(data => {
        renderMemberDrawer(data);
      })
      .catch(err => {
        if (drawerContent) {
          drawerContent.innerHTML = `
            <div class="p-4 text-center">
              <div class="text-danger mb-2"><i data-lucide="alert-circle" style="width: 36px; height: 36px;"></i></div>
              <h6 class="fw-bold text-dark">Failed to load member profile</h6>
              <p class="text-muted small">${err.message}</p>
              <button class="btn btn-sm btn-fn-primary" onclick="window.openMemberDrawer(${memberId})">Try Again</button>
            </div>
          `;
          initLucide();
        }
      });
  };

  function renderMemberDrawer(m) {
    const drawerTitle = document.getElementById('fnDrawerTitle');
    const drawerSubtitle = document.getElementById('fnDrawerSubtitle');
    const drawerFooter = document.getElementById('fnDrawerFooter');
    const drawerContent = document.getElementById('fnDrawerContent');

    if (drawerTitle) drawerTitle.textContent = m.full_name;
    if (drawerSubtitle) drawerSubtitle.textContent = `ID: ${m.member_id} • ${m.branch_name}`;

    const statusBadge = m.status === 'ACTIVE'
      ? `<span class="fn-badge fn-badge-success"><span class="fn-status-dot active"></span> Active Member</span>`
      : (m.status === 'EXPIRED'
        ? `<span class="fn-badge fn-badge-danger">Expired</span>`
        : `<span class="fn-badge fn-badge-warning">${m.status_display}</span>`);

    let planSnippet = '';
    if (m.current_plan) {
      const daysLeft = m.current_plan.days_remaining;
      const daysBadge = daysLeft <= 7
        ? `<span class="badge bg-danger">${daysLeft} days left</span>`
        : `<span class="badge bg-success">${daysLeft} days left</span>`;

      planSnippet = `
        <div class="p-3 bg-light rounded-3 mb-3 border">
          <div class="d-flex justify-content-between align-items-center mb-1">
            <span class="text-muted small">Current Subscription</span>
            ${daysBadge}
          </div>
          <div class="fw-bold fs-6 text-dark">${m.current_plan.name}</div>
          <div class="text-muted small mt-1">
            Valid: <span class="text-dark fw-semibold">${m.current_plan.start_date} – ${m.current_plan.end_date}</span>
          </div>
        </div>
      `;
    } else {
      planSnippet = `
        <div class="p-3 bg-light rounded-3 mb-3 border text-center">
          <div class="text-muted small">No active membership subscription assigned.</div>
          <a href="${m.urls.renew}" class="btn btn-sm btn-fn-accent mt-2">Assign / Renew Plan</a>
        </div>
      `;
    }

    let qrSnippet = '';
    if (m.qr_code_url) {
      qrSnippet = `
        <div class="text-center p-3 bg-light rounded-3 mb-3 border">
          <div class="text-muted small mb-2 fw-semibold">Digital Attendance Pass</div>
          <img src="${m.qr_code_url}" alt="QR Pass" style="width: 140px; height: 140px; border-radius: 8px; border: 1px solid #E2E8F0; background: #FFF; padding: 4px;" class="mb-2">
          <div>
            <a href="${m.qr_code_url}" download="FitNova_Pass_${m.member_id}.png" class="btn btn-sm btn-outline-secondary py-1 px-2" style="font-size: 0.76rem;">
              <i data-lucide="download" style="width: 13px;"></i> Download Pass
            </a>
          </div>
        </div>
      `;
    }

    // Memberships list
    let memList = '';
    if (m.memberships && m.memberships.length > 0) {
      memList = m.memberships.map(sub => `
        <div class="d-flex justify-content-between align-items-center py-2 border-bottom small">
          <div>
            <div class="fw-semibold text-dark">${sub.plan_name}</div>
            <div class="text-muted" style="font-size: 0.72rem;">${sub.dates}</div>
          </div>
          <span class="fn-badge ${sub.status === 'ACTIVE' ? 'fn-badge-success' : 'fn-badge-muted'}">${sub.status_display}</span>
        </div>
      `).join('');
    } else {
      memList = `<div class="text-muted small py-2 text-center">No past memberships on record.</div>`;
    }

    // Payments list
    let payList = '';
    if (m.payments && m.payments.length > 0) {
      payList = m.payments.map(p => `
        <div class="d-flex justify-content-between align-items-center py-2 border-bottom small">
          <div>
            <div class="fw-semibold text-dark font-monospace">${p.transaction_id}</div>
            <div class="text-muted" style="font-size: 0.72rem;">${p.date} • ${p.method}</div>
          </div>
          <div class="text-end">
            <div class="fw-bold text-dark">${m.currency}${p.amount}</div>
            <span class="badge ${p.status === 'COMPLETED' ? 'bg-success' : 'bg-warning'}" style="font-size: 0.68rem;">${p.status_display}</span>
          </div>
        </div>
      `).join('');
    } else {
      payList = `<div class="text-muted small py-2 text-center">No payment transactions found.</div>`;
    }

    if (drawerContent) {
      drawerContent.innerHTML = `
        <!-- Profile Banner -->
        <div class="d-flex align-items-center gap-3 mb-3 pb-3 border-bottom">
          <div class="fn-avatar" style="width: 56px; height: 56px; font-size: 1.3rem;">
            ${m.initials}
          </div>
          <div class="flex-grow-1">
            <div class="d-flex align-items-center gap-2">
              <h5 class="fw-bold text-dark mb-0">${m.full_name}</h5>
              ${statusBadge}
            </div>
            <div class="text-muted small mt-1">
              <span>${m.email}</span> • <span>${m.phone}</span>
            </div>
          </div>
        </div>

        <!-- Tabbed Navigation inside Drawer -->
        <div class="fn-drawer-nav-tabs">
          <button class="fn-drawer-tab-btn active" onclick="switchDrawerTab(this, 'drawerTabProfile')">
            <i data-lucide="user" style="width: 14px;"></i> Overview
          </button>
          <button class="fn-drawer-tab-btn" onclick="switchDrawerTab(this, 'drawerTabPlan')">
            <i data-lucide="credit-card" style="width: 14px;"></i> Membership & QR
          </button>
          <button class="fn-drawer-tab-btn" onclick="switchDrawerTab(this, 'drawerTabHistory')">
            <i data-lucide="clock" style="width: 14px;"></i> History
          </button>
        </div>

        <!-- Tab 1: Profile & Contact Details -->
        <div id="drawerTabProfile" class="drawer-tab-pane">
          ${planSnippet}
          <div class="p-3 bg-light rounded-3 small">
            <h6 class="fw-bold text-dark mb-2" style="font-size: 0.8rem; text-transform: uppercase; letter-spacing: 0.04em;">Contact & Demographics</h6>
            <div class="d-flex justify-content-between py-1 border-bottom">
              <span class="text-muted">Phone:</span>
              <a href="tel:${m.phone}" class="fw-semibold text-primary text-decoration-none">${m.phone}</a>
            </div>
            <div class="d-flex justify-content-between py-1 border-bottom">
              <span class="text-muted">Email:</span>
              <a href="mailto:${m.email}" class="fw-semibold text-primary text-decoration-none">${m.email}</a>
            </div>
            <div class="d-flex justify-content-between py-1 border-bottom">
              <span class="text-muted">Gender:</span>
              <span class="fw-semibold text-dark">${m.gender}</span>
            </div>
            <div class="d-flex justify-content-between py-1 border-bottom">
              <span class="text-muted">Date of Birth:</span>
              <span class="fw-semibold text-dark">${m.dob}</span>
            </div>
            <div class="d-flex justify-content-between py-1 border-bottom">
              <span class="text-muted">Blood Group:</span>
              <span class="fw-semibold text-dark">${m.blood_group}</span>
            </div>
            <div class="d-flex justify-content-between py-1 border-bottom">
              <span class="text-muted">Joined:</span>
              <span class="fw-semibold text-dark">${m.joined_date}</span>
            </div>
            <div class="d-flex justify-content-between py-1 border-bottom">
              <span class="text-muted">Assigned Coach:</span>
              <span class="fw-semibold text-dark">${m.trainer_name}</span>
            </div>
            <div class="d-flex justify-content-between py-1">
              <span class="text-muted">Emergency:</span>
              <span class="fw-semibold text-dark">${m.emergency_name} (${m.emergency_phone})</span>
            </div>
          </div>

          <div class="mt-3 p-3 bg-light rounded-3 small">
            <h6 class="fw-bold text-dark mb-1" style="font-size: 0.8rem; text-transform: uppercase; letter-spacing: 0.04em;">Fitness Target</h6>
            <p class="text-muted mb-2">${m.fitness_goals}</p>
            <h6 class="fw-bold text-dark mb-1" style="font-size: 0.8rem; text-transform: uppercase; letter-spacing: 0.04em;">Medical / Health Notes</h6>
            <p class="text-muted mb-0">${m.medical_history}</p>
          </div>
        </div>

        <!-- Tab 2: Subscription & QR Pass -->
        <div id="drawerTabPlan" class="drawer-tab-pane d-none">
          ${planSnippet}
          ${qrSnippet}
        </div>

        <!-- Tab 3: History -->
        <div id="drawerTabHistory" class="drawer-tab-pane d-none">
          <h6 class="fw-bold text-dark mb-2 small text-uppercase" style="letter-spacing: 0.05em;">Membership Timeline</h6>
          <div class="mb-4 bg-light p-3 rounded-3">
            ${memList}
          </div>

          <h6 class="fw-bold text-dark mb-2 small text-uppercase" style="letter-spacing: 0.05em;">Payment Transactions</h6>
          <div class="bg-light p-3 rounded-3">
            ${payList}
          </div>
        </div>
      `;
      initLucide();
    }

    if (drawerFooter) {
      drawerFooter.innerHTML = `
        <div>
          <button type="button" class="btn btn-sm btn-outline-danger" onclick="triggerDeleteModal('${m.id}', '${m.full_name}')">
            <i data-lucide="trash-2" style="width: 14px;"></i> Delete
          </button>
        </div>
        <div class="d-flex gap-2">
          <a href="${m.urls.edit}" class="btn btn-sm btn-fn-outline">
            <i data-lucide="edit-3" style="width: 14px;"></i> Edit
          </a>
          <a href="${m.urls.renew}" class="btn btn-sm btn-fn-accent">
            <i data-lucide="repeat" style="width: 14px;"></i> Renew Plan
          </a>
          <a href="${m.urls.detail}" class="btn btn-sm btn-fn-primary">
            <span>Full Profile</span> &rarr;
          </a>
        </div>
      `;
      initLucide();
    }
  }

  // Drawer tab switcher helper
  window.switchDrawerTab = function (btn, paneId) {
    const tabs = drawer.querySelectorAll('.fn-drawer-tab-btn');
    tabs.forEach(t => t.classList.remove('active'));
    btn.classList.add('active');

    const panes = drawer.querySelectorAll('.drawer-tab-pane');
    panes.forEach(p => p.classList.add('d-none'));

    const targetPane = document.getElementById(paneId);
    if (targetPane) targetPane.classList.remove('d-none');
    initLucide();
  };
}

/* Modal Helper for Deleting Member */
window.triggerDeleteModal = function (memberId, memberName) {
  const modalEl = document.getElementById('deleteConfirmModal');
  if (!modalEl) return;

  const form = document.getElementById('deleteMemberForm');
  const nameSpan = document.getElementById('deleteMemberName');

  if (form) form.action = `/members/${memberId}/delete/`;
  if (nameSpan) nameSpan.textContent = memberName;

  if (typeof bootstrap !== 'undefined' && bootstrap.Modal) {
    const modal = new bootstrap.Modal(modalEl);
    modal.show();
  }
};
