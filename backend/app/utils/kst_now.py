from datetime import datetime
import pytz

KST = pytz.timezone('Asia/Seoul')

def kst_now():
    return datetime.now(KST)
