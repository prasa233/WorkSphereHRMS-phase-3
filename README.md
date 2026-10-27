WorkSphere HRMS — Phase 3 (Short Requirements)
Goal
Add automation, analytics, and smart employee features to WorkSphere.
Modules 14–20
14. Attendance & Shift Management
- Tables: Shifts(id, name, start_time, end_time), Employee_Shifts(id, employee_id, shift_id)
- Assign shifts and display employee schedules.
- Automate attendance and detect late check-ins or early check-outs.
15. Leave Calendar & Team View
- Show team leave dates and employee availability.
- Highlight approved leave and help prevent scheduling conflicts.
- Provide a leave calendar and team dashboard.
16. Document Management
- Table: Documents(id, employee_id, file_name, file_url, uploaded_at)
- Upload, view, and download employee documents securely.
- Provide document upload and listing pages.
17. Performance Management
- Table: Performance(id, employee_id, review_period, rating, feedback, created_at)
- Create reviews, track ratings, and maintain feedback history.
- Provide a performance review and feedback interface.
18. Analytics & Reports
- Report on attendance, leave, performance, and departments.
- Provide charts and a dashboard with date and department filters.
19. Notifications & Alerts
- Notify users about late attendance, leave approvals, and payroll processing.
- Document-expiry alerts are optional.
- Display notifications with real-time updates.
20. Employee Search & Filters
- Search by employee name, department, and role.
- Filter by status, attendance, and performance.
- Provide search controls and filtered results.
Database
New tables: Shifts, Employee_Shifts, Documents, Performance

Existing tables: Users, Employees, Attendance, Leaves, Payroll, Notifications, Leave_Policies, Leave_Balance
Security
- JWT authentication and role-based authorization.
- Validate API inputs with Pydantic.
- Secure document uploads, storage, and access.
- Store secrets in environment configuration.
Deliverables Checklist
- [ ] Shift assignment and attendance automation
- [ ] Leave calendar and team availability
- [ ] Secure document management
- [ ] Performance reviews and ratings
- [ ] Analytics dashboard and reports
- [ ] Smart notifications and alerts
- [ ] Advanced employee search and filters
