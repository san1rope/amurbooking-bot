from .start import router as r_start
from .accounts import router as r_accounts
from .booking import router as r_booking

routers = [
    r_start,
    r_accounts,
    r_booking
]
