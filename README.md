# Backend Setup Instructions

## Quick Start

1. **Create virtual environment**
   ```bash
   python -m venv venv
   ```

2. **Activate virtual environment**
   - Windows (PowerShell): `.\venv\Scripts\Activate.ps1`
   - Windows (CMD): `.\venv\Scripts\activate.bat`
   - Linux/Mac: `source venv/bin/activate`

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Setup environment variables**
   ```bash
   cp .env.example .env
   ```
   Edit `.env` with your configuration

5. **Run migrations**
   ```bash
   python manage.py makemigrations
   python manage.py migrate
   ```

6. **Create superuser**
   ```bash
   python manage.py createsuperuser
   ```

7. **Run development server**
   ```bash
   python manage.py runserver
   ```

## API Endpoints

Base URL: `http://localhost:8000/api/`

### Authentication
- `POST /api/auth/register/` - Register user
- `POST /api/auth/login/` - Login
- `GET /api/auth/me/` - Get current user

### Donations
- `GET /api/donations/` - List donations
- `POST /api/donations/` - Create donation
- `GET /api/donations/{id}/` - Get donation
- `PATCH /api/donations/{id}/` - Update donation
- `DELETE /api/donations/{id}/` - Delete donation

### Locations
- `GET /api/locations/` - List locations
- `POST /api/locations/` - Create/Update location
- `GET /api/locations/affected_users/` - Get affected users locations

## Testing

Run tests with:
```bash
python manage.py test
```

## Admin Panel

Access at: `http://localhost:8000/admin/`

Use superuser credentials to login.
