from datetime import time, timedelta, datetime

from django.core.management.base import BaseCommand
from orders.models import Branch, BranchTimeSlotCapacity

class Command(BaseCommand):
    help = "Initialize default time slots for each branch (with default max_capacity=20)"

    def handle(self, *args, **kwargs):
        self.stdout.write("🔄 開始建立每個分店的預設時段...")

        for branch in Branch.objects.all():
            self.stdout.write(f"處理分店: {branch.name}")
            self.create_default_time_slots(branch)

        self.stdout.write(self.style.SUCCESS("✅ 所有分店的預設時段建立完成！"))

    def create_default_time_slots(self, branch):
        for weekday in range(7):  # 0=Monday, 6=Sunday
            if weekday < 5:
                periods = [(time(11, 0), time(14, 30)), (time(17, 0), time(22, 30))]
            else:
                periods = [(time(11, 0), time(22, 30))]

            for start, end in periods:
                current = datetime.combine(datetime.today(), start)
                end_dt = datetime.combine(datetime.today(), end)

                while current + timedelta(minutes=30) <= end_dt:
                    slot_time = current.time()
                    obj, created = BranchTimeSlotCapacity.objects.get_or_create(
                        branch=branch,
                        weekday=weekday,
                        time_slot=slot_time,
                        defaults={'max_capacity': 20, 'available': True}
                    )
                    if created:
                        self.stdout.write(f"  ➕ 新增時段: {weekday=} {slot_time=}")
                    current += timedelta(minutes=30)