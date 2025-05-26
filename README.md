# MLRMS
# 🏥 Medico-Legal Record Management System

A secure, role-based web application to streamline the upload, access, approval, and management of medico-legal case records by authorized personnel including **Hospital Administrators**,**Healthcare Providers**, **Legal Professionals**, **Law Enforcement Officers**, **Patients & Families**, and **Insurance Companies**.


## 🏗️ Architecture

- Frontend: HTML5, CSS3, JavaScript
- Backend: Flask (Python)
- Database: SQLite
- Authentication: Session-based login
- File Uploads: Stored locally with secure file handling

---

## 🖥️ Roles & Dashboards

Each user role has a dedicated dashboard and view-specific access:

| Role | Key Functionalities |
|------|----------------------|
| **Hospital Administrator** | Upload & View medical records, manage requests, approve/reject access to records|
|**Healthcare Providers** | View records |
| **Law Enforcement Officer** |Upload Legal records, request & view medical records  |
| **Legal Professional** | request & View legal & Medical records |
| **Patients & Families** | Search own case ID, request access to view/download ,claim inusrance by requesting to insurance company|
| **Insurance Companies** | View approved policyholder records, download documentation,verify claim req |

---

## 💽 Tech Stack

| Layer | Technology |
|-------|------------|
| Frontend | HTML5, CSS3, JavaScript |
| Backend | Flask (Python 3.9+) |
| Database | SQLite3 |
| Hosting/Server | Flask’s built-in dev server |
| Testing | Postman |
| Editor | VS Code / PyCharm |

---

## 📋 Software Requirements

| Software | Version |
|----------|---------|
| OS | Windows 10 / Ubuntu 20.04+ |
| Python | 3.9+ |
| Flask | 2.2+ |
| SQLite | 3.36+ |
| Browser | Chrome / Firefox |
| Tools | Git, Postman, pip |

---


