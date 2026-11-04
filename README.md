# FitNova – Premium Gym Management SaaS Platform

FitNova is an enterprise-grade, multi-role Gym Management SaaS platform built with **Python 3.13**, **Django 6**, **Django REST Framework**, and a commercial-quality responsive frontend.

---

## 🎨 1. Design System & Brand Identity

FitNova features a completely custom, unique visual identity (no generic admin templates):
- **Background**: `#F7F8FC`
- **Primary Navy**: `#172554`
- **Accent Violet**: `#7657E8`
- **Success Emerald**: `#10B981`
- **Warning Amber**: `#F59E0B`
- **Danger Rose**: `#EF4444`
- **Typography**: Inter (Google Fonts)
- **Icons**: Lucide Icons
- **Cards Geometry**: 16px rounded borders (`border-radius: 16px; border: 1px solid #E2E8F0; box-shadow: 0 4px 20px -2px rgba(23, 37, 84, 0.05);`)
- **Animations**: Fluid hover micro-interactions, responsive collapsible sidebar with persistent state.

---

## 🚀 2. Pre-Configured Demo Accounts

The database comes pre-seeded with rich, realistic data across all modules:

| Role | Username | Password | Purpose |
| :--- | :--- | :--- | :--- |
| **Gym Admin / Super Admin** | `admin` | `FitNova@Admin2026` | Full SaaS access, 8 KPI cards, 5 charts, settings |
| **Receptionist / Staff** | `staff1` | `Staff@FitNova2026` | Member desk, QR check-ins, payments & invoices |
| **Trainer / Coach** | `alex_trainer` | `Trainer@FitNova2026` | Trainer portal, workout splits, assigned athletes |
| **Gym Member** | `john_doe` | `Member@FitNova2026` | Member portal, digital QR pass, workout & diet plan |

---

## 🗂️ 3. Main Navigation & Functional Modules

The collapsible sidebar includes all **15 functional sections**:

1. **Dashboard** (`/`):
   - 8 Real-time DB Stat Cards: Total Members, Active Members, New Registrations, Total Revenue, Pending Payments, Expiring Memberships, Today's Attendance, Monthly Growth (%).
   - 5 Interactive Chart.js charts: Monthly Revenue, Weekly Attendance, Membership Distribution, Member Growth, and Payment Analytics.
   - Dynamic tables: Recent Registrations, Recent Transactions, Upcoming Expirations (next 14 days), and Trainer Performance.
2. **Members** (`/members/`):
   - Complete CRUD, search, filter by status and plan, pagination.
   - Detailed athlete profile with photo, contact info, emergency contacts, medical records, goals, and downloadable QR pass.
3. **Membership Plans** (`/memberships/plans/`):
   - Multi-tier plans (Monthly, Quarterly, Half-Yearly, Yearly, VIP).
   - Privileges, pricing, signup fees, popular badges, and automated expiry dates.
   - Direct member renewal workflow (`/memberships/renew/<id>/`).
4. **Attendance & QR System** (`/attendance/`):
   - Live camera QR code scanner (`html5-qrcode`) and manual ID check-in (`/attendance/scanner/`).
   - Duplicate check-in prevention on the same calendar day.
   - Automatic check-out and session duration tracking.
   - Active membership validation (blocks expired passes).
5. **Trainers** (`/trainers/`):
   - Trainer directory, specializations, ratings, hourly coaching rates, and athlete assignments.
6. **Workout Management** (`/fitness/workouts/`):
   - Multi-day workout splits (Push-Pull-Legs, Full Body), exercise sets, reps, and rest timers.
7. **Diet Management** (`/fitness/diets/`):
   - Macronutrient targets (Calories, Protein, Carbs, Fats, Water) and scheduled meals.
8. **Classes & Bookings** (`/classes/`):
   - Group studio classes (Spinning, Yoga, CrossFit, HIIT) with room, trainer, schedule, and live seat capacity limit tracking.
9. **Payments** (`/payments/`):
   - Payment processing (Cash, UPI, Credit Card, Debit Card, Net Banking).
   - Duplicate transaction prevention.
10. **Invoices** (`/payments/invoices/`):
    - Commercial PDF-styled printable tax invoices (`INV-2026-xxxxx`) with gym organization branding.
11. **Expenses** (`/payments/expenses/`):
    - Operating expense tracking (Rent, Equipment, Payroll, Utilities, Cleaning, Marketing).
12. **Leads & CRM** (`/crm/`):
    - Sales inquiry pipeline across stages (New, Contacted, Trial Scheduled, Converted, Lost).
13. **Notifications** (`/notifications/`):
    - Notification center, unread count badge, expiry alerts, and payment receipts.
14. **Reports & Analytics** (`/reports/`):
    - Consolidated P&L statement, revenue vs expenses, net profit margin, and retention rates.
15. **Settings** (`/settings/`):
    - Multi-gym organization profile, branch addresses, tax/GST ID, and currency symbol.

---

## 💻 4. Windows CMD / PowerShell Setup Instructions

### 1. Run Migrations
```cmd
python manage.py migrate
```

### 2. Seed Rich Demo Data (Optional / Fresh Start)
```cmd
python manage.py seed_fitnova
```

### 3. Run Unit Tests
```cmd
python manage.py test
```

### 4. Start Development Server
```cmd
python manage.py runserver 127.0.0.1:8000
```
Then open your browser at: **`http://127.0.0.1:8000/`**

---

## 🛢️ 5. PostgreSQL 18 Configuration

By default, FitNova runs out-of-the-box with SQLite (`db.sqlite3`). To connect directly to **PostgreSQL 18**:
Set the `DATABASE_URL` environment variable:

In Windows CMD:
```cmd
set DATABASE_URL=postgres://postgres:your_password@localhost:5432/fitnova_db
python manage.py migrate
```

In PowerShell:
```powershell
$env:DATABASE_URL="postgres://postgres:your_password@localhost:5432/fitnova_db"
python manage.py migrate
```

---

## 🛡️ 6. Security Architecture
- Role-Based Access Control (`role_required`, `admin_only`, `staff_or_admin`, `trainer_or_above`).
- Organization-level data isolation scoping on all queries and DRF ViewSets.
- CSRF protection across all forms and AJAX/QR camera scanner endpoints.
- Password hashing with PBKDF2.
