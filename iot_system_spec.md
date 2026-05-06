# 📡 System IoT – Serwer zbierania danych (FastAPI)

## 1. Opis systemu

Celem systemu jest stworzenie bezpiecznego i niezawodnego rozwiązania do zbierania danych z urządzeń IoT (Raspberry Pi), ich przetwarzania oraz udostępniania do wizualizacji.

System oparty jest na architekturze klient–serwer, gdzie:
- urządzenia IoT wysyłają dane pomiarowe,
- serwer backendowy odbiera i zapisuje dane,
- baza danych przechowuje informacje,
- Grafana wizualizuje dane poprzez backend.

System działa w środowisku wirtualnym (Proxmox) i wykorzystuje pfSense jako zaporę sieciową.

---

## 2. Architektura systemu

### Główne komponenty:

- pfSense – firewall i routing
- Backend (FastAPI) – REST API
- Database (PostgreSQL)
- Grafana – wizualizacja
- Raspberry Pi – urządzenia IoT

### Schemat:

Raspberry Pi → pfSense → FastAPI → Database  
Grafana → FastAPI

---

## 3. Funkcjonalności

### Odbieranie danych
POST /api/v1/measurements

### Certyfikaty
POST /api/v1/certificates/request  
POST /api/v1/certificates/renew  
POST /api/v1/certificates/revoke  

### Dane dla Grafany
GET /api/v1/measurements  
GET /api/v1/metrics  

### Monitoring
GET /api/v1/health  

---

## 4. Wymagania funkcjonalne

- odbiór danych z IoT
- zapis do bazy
- wizualizacja w Grafanie
- obsługa certyfikatów
- autoryzacja urządzeń

---

## 5. Wymagania niefunkcjonalne

### Bezpieczeństwo
- TLS
- brak dostępu do DB z Internetu
- firewall pfSense

### Niezawodność
- retry
- ACK

---

## 6. Model danych

devices  
measurements  
certificates  

---

## 7. Technologie

FastAPI, PostgreSQL, Grafana, pfSense, Proxmox

---

## 8. Podsumowanie

Bezpieczny system IoT z izolacją bazy i kontrolą dostępu.
