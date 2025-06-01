from datetime import time, timedelta, datetime

from django.core.management.base import BaseCommand
from orders.models import Branch, BranchTimeSlotCapacity

class Command(BaseCommand):
    help = "Initialize default branches and their default time slots (with default max_capacity=20)"

    def handle(self, *args, **kwargs):
        self.stdout.write("🏢 開始建立預設分店...")
        self.create_default_branches()

        self.stdout.write("🔄 開始建立每個分店的預設時段...")
        for branch in Branch.objects.all():
            self.stdout.write(f"處理分店: {branch.name}")
            self.create_default_time_slots(branch)

        self.stdout.write(self.style.SUCCESS("✅ 分店與其預設時段建立完成！"))

    def create_default_branches(self):
        default_branches = [
            {
                "name": "Xinzhuang Zhongzheng Store",
                "region": "North",
                "address": "1F, No. 52, Zhongzheng Road, Xinzhuang District, New Taipei City",
                "phone": "(02) 1335-4598",
                "map_embed_html": """<iframe src="https://www.google.com/maps/embed?pb=!1m10!1m8!1m3!1d3614.8106023451005!2d121.4614521!3d25.0405008!3m2!1i1024!2i768!4f13.1!5e0!3m2!1sen!2stw!4v1748104911360!5m2!1sen!2stw" width="600" height="450" style="border:0;" allowfullscreen="" loading="lazy" referrerpolicy="no-referrer-when-downgrade"></iframe>""",
            },
            {
                "name": "Taipei Xinyi Store",
                "region": "North",
                "address": "No. 88, Songgao Road, Xinyi District, Taipei City",
                "phone": "(02) 2789-1234",
                "map_embed_html": """<iframe src="https://www.google.com/maps/embed?pb=!1m18!1m12!1m3!1d3614.858165768201!2d121.57163799999998!3d25.038887!2m3!1f0!2f0!3f0!3m2!1i1024!2i768!4f13.1!3m3!1m2!1s0x3442aba4ceac2fd5%3A0x17ca62d2a6cd55d1!2zMTEw5Y-w5YyX5biC5L-h576p5Y2A5p2-6auY6LevODjomZ8!5e0!3m2!1szh-TW!2stw!4v1748194129529!5m2!1szh-TW!2stw" width="600" height="450" style="border:0;" allowfullscreen="" loading="lazy" referrerpolicy="no-referrer-when-downgrade"></iframe>"""
            },
            {
                "name": "Banqiao Wenhua Store",
                "region": "North",
                "address": "No. 111, Section 1, Wenhua Road, Banqiao District, New Taipei City",
                "phone": "(02) 2222-3333",
                "map_embed_html": """<iframe src="https://www.google.com/maps/embed?pb=!1m18!1m12!1m3!1d3615.5660434419087!2d121.46159879999998!3d25.014857600000003!2m3!1f0!2f0!3f0!3m2!1i1024!2i768!4f13.1!3m3!1m2!1s0x3442a81bc1928f09%3A0x2e0691fe15a63139!2zMjIw5paw5YyX5biC5p2_5qmL5Y2A5paH5YyW6Lev5LiA5q61MTEx6Jmf!5e0!3m2!1szh-TW!2stw!4v1748618662710!5m2!1szh-TW!2stw" width="600" height="450" style="border:0;" allowfullscreen="" loading="lazy" referrerpolicy="no-referrer-when-downgrade"></iframe>"""
            },
            {
                "name": "Zhongli Zhongzheng Store",
                "region": "North",
                "address": "No. 23, Zhongzheng Road, Zhongli District, Taoyuan City",
                "phone": "(03) 456-7890",
                "map_embed_html": """<iframe src="https://www.google.com/maps/embed?pb=!1m18!1m12!1m3!1d3617.351143690529!2d121.22468180000001!3d24.954164999999996!2m3!1f0!2f0!3f0!3m2!1i1024!2i768!4f13.1!3m3!1m2!1s0x346822490690b6dd%3A0xe59300cc503a71ea!2zMzIw5qGD5ZyS5biC5Lit5aOi5Y2A5Lit5q2j6LevMjPomZ8!5e0!3m2!1szh-TW!2stw!4v1748618752448!5m2!1szh-TW!2stw" width="600" height="450" style="border:0;" allowfullscreen="" loading="lazy" referrerpolicy="no-referrer-when-downgrade"></iframe>"""
            },
            {
                "name": "Taichung Gongyi Store",
                "region": "Central",
                "address": "No. 50, Section 2, Gongyi Road, Nantun District, Taichung City",
                "phone": "(04) 9876-5432",
                "map_embed_html": """<iframe src="https://www.google.com/maps/embed?pb=!1m18!1m12!1m3!1d3640.5908900203262!2d120.65110059999999!3d24.1510015!2m3!1f0!2f0!3f0!3m2!1i1024!2i768!4f13.1!3m3!1m2!1s0x34693d9657c973a5%3A0xfe848f69419cf963!2zNDA45Y-w5Lit5biC5Y2X5bGv5Y2A5YWs55uK6Lev5LqM5q61NTDomZ8!5e0!3m2!1szh-TW!2stw!4v1748618797734!5m2!1szh-TW!2stw" width="600" height="450" style="border:0;" allowfullscreen="" loading="lazy" referrerpolicy="no-referrer-when-downgrade"></iframe>"""
            },
            {
                "name": "Kaohsiung Hanshin Store",
                "region": "Southern",
                "address": "No. 266, Chenggong 1st Road, Qianjin District, Kaohsiung City",
                "phone": "(07) 6543-2100",
                "map_embed_html": """<iframe src="https://www.google.com/maps/embed?pb=!1m18!1m12!1m3!1d3682.9221426698987!2d120.2960937!3d22.6193824!2m3!1f0!2f0!3f0!3m2!1i1024!2i768!4f13.1!3m3!1m2!1s0x346e047fcbcbf27b%3A0x8ff68c0076ebc3f!2zODAx6auY6ZuE5biC5YmN6YeR5Y2A5oiQ5Yqf5LiA6LevMjY2LTPomZ8!5e0!3m2!1szh-TW!2stw!4v1748618859684!5m2!1szh-TW!2stw" width="600" height="450" style="border:0;" allowfullscreen="" loading="lazy" referrerpolicy="no-referrer-when-downgrade"></iframe>"""
            },
            
        ]

        for branch_data in default_branches:
            branch, created = Branch.objects.get_or_create(
                name=branch_data["name"],
                defaults={
                    "region": branch_data["region"],
                    "address": branch_data["address"],
                    "phone": branch_data["phone"],
                    "is_reservable": True,
                    "is_orderable": True,
                    "map_embed_html": branch_data["map_embed_html"],
                }
            )
            if created:
                self.stdout.write(f"  ➕ 新增分店: {branch.name}")
            else:
                self.stdout.write(f"  ✅ 已存在分店: {branch.name}")

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
                        defaults={
                            'max_capacity': 20,
                            'available': True,
                            'is_orderable': True,             
                            'max_orderable': 10,         
                        }
                    )
                    if created:
                        pass  #self.stdout.write(f"  ➕ 新增時段: {weekday=} {slot_time=}")
                    current += timedelta(minutes=30)