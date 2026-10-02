# 🌐 رادار خبری تاب‌آور و مستقل (Resilient 30-Min Media Aggregator)

سامانه مانیتورینگ چندرسانه‌ای خودکار از منابع مستقل فارسی، کانال‌های تلگرام، توییتر و خبرگزاری‌های مادر بین‌المللی با **هزینه صفر (Zero LLM Tokens)** و سازگار با محدودیت‌های شدید اینترنت ملی در ایران.

⏱ **وضعیت پایپ‌لاین:** فعال بر روی Server 2 (ARM64) | **آخرین همگام‌سازی:** `2026-10-02 04:06 IRST`

### 🚀 راه‌های دسترسی سریع در شرایط فیلترینگ و اینترنت ملی:
1. **فایل متنی سبک (Raw Markdown):** دریافت مستقیم [`news/latest.md`](news/latest.md) از طریق CDN گیت‌هاب با حجم اندک.
2. **آرشیو تصاویر محلی:** مشاهده رسانه‌ها در پوشه `media/` با امکان بارگذاری آفلاین.
3. **همگام‌سازی گیت (Git CLI):** دریافت با دستور `git pull` حتی با سرعت‌های پایین زیر ۵۰ کیلوبیت.

---

## 📌 مهم‌ترین سرخط‌های جاری

- **`بی‌بی‌سی فارسی`** [پوتین ابراز امیدواری کرد که تنگه هرمز باز و تحریم‌های ایران لغو شود](https://www.bbc.co.uk/persian/live/cmd797py92ret?at_medium=RSS&at_campaign=rss) — `04:06 IRST` / `00:36 UTC`
  > ولادیمیر پوتین، رئیس جمهور روسیه که روز پنجشنبه در یک کنفرانس خبری مفصل شرکت کرده بود ابراز امیدواری کرده که تنگه هرمز هر چه زودتر باز و تحریم‌های ایران لغو شود. بنیامین نتانیاهو مدعی شده است که کمک خلبان پرواز فلای‌دوبی که با چاقو به خلبان حمله کرده بود تحت «آموزه‌های افراطی ...

  ![Media](media/2026-10-02/0be67a14f4a0fbcb.jpg)
- **`بی‌بی‌سی فارسی`** [آنچه گذشت؛ آمریکا شرکت‌های حمل و نقل ریلی و خودروسازی ایران را تحریم کرد](https://www.bbc.co.uk/persian/live/cm9w4wrzpv51t?at_medium=RSS&at_campaign=rss) — `04:06 IRST` / `00:36 UTC`
  > وزارت دارایی آمریکا اعلام کرده که دور تازه و گسترده‌ای از تحریم‌ها علیه ایران را در چارچوب «عملیات طرد اقتصادی» اعمال می‌کند. این تحریم‌ها این بار فراتر از نفت و بخش مالی رفته و به طور مشخص صنایع خودروسازی، راه‌آهن، تولید و فولاد ایران را هدف قرار می‌دهد. در میان مهم‌ترین شرکت...

  ![Media](media/2026-10-02/14ce34ebb9f2cb9d.jpg)
- **`@IranintlTV (ایران اینترنشنال (تلگرام))`** [مایک والتز، سفیر آمریکا در سازمان ملل، در نشست مجمع عمومی این سازمان گفت جمهوری اسلامی قوانین را نقض کرده و هرگز حاضر نی...](https://t.me/IranintlTV/360254) — `04:02 IRST` / `00:32 UTC`
  > مایک والتز، سفیر آمریکا در سازمان ملل، در نشست مجمع عمومی این سازمان گفت جمهوری اسلامی قوانین را نقض کرده و هرگز حاضر نیست از «جاه‌طلبی‌های هسته‌ای» خود دست بکشد.

والتز با اشاره به آژانس بین‌المللی انرژی اتمی گفت: «کافی است نظر آژانس بین‌المللی انرژی اتمی را بپرسید.» او افزود...

  ![Media](media/2026-10-02/d9bd8907a5c4a3e1.jpg)
- **`ایران اینترنشنال`** [بحران کمبود انرژی؛ زمستان سخت ایران در راه است](https://www.iranintl.com/202610021443) — `03:31 IRST` / `00:01 UTC`
  > ایران در آستانه زمستانی قرار گرفته که کمبود مزمن گاز، این‌بار با کاهش ظرفیت تولید و آسیب‌دیدگی زیرساخت‌ها پس از جنگ تشدید شده است. شبکه گازی که زمستان گذشته در روزهای اوج مصرف با کمبودی تا ۳۰۰ میلیون مترمکعب روبه‌رو بود، امسال با ظرفیت کمتر به استقبال فصل سرما می‌رود.

  ![Media](media/2026-10-02/fd2bd7fda86cf46f.jpg)
- **`Reuters Wire`** [Putin says the world is living through a dangerous moment, warns West not to escalate - Reuters](https://news.google.com/rss/articles/CBMiwgFBVV95cUxNbmRoRDA2R19zaDc4RVpPclJ2UkNVS0hqZGdfbkJobzJHR015RmhJMDh1UFhIcXdaN3gyLXpEN05xN1Q0N0tlTFZvTk1WcWM4ZHJVak10d0hFQ3oyZG50OHNPLThHR2JXWExldEVRVzVYclJYN3VpeDVXaW1ENVByNjhwYi15M3lMNnU4Ull0ZDlJUWJkMVhXSVk0dEw2ZkxKTFJFeEVtSVV5b2l2YkZOXzJLaFo2Q3FzUHhlcXFQanhhUQ?oc=5) — `03:29 IRST` / `23:59 UTC`
  > Putin says the world is living through a dangerous moment, warns West not to escalate    Reuters
- **`@IranintlTV (ایران اینترنشنال (تلگرام))`** [داده‌های ردیابی نفتکش‌ها نشان می‌دهد صادرات محموله‌های جدید نفت ایران عملا متوقف شده، در حالی که صادرات نفت خام کشورهای ...](https://t.me/IranintlTV/360252) — `03:20 IRST` / `23:50 UTC`
  > داده‌های ردیابی نفتکش‌ها نشان می‌دهد صادرات محموله‌های جدید نفت ایران عملا متوقف شده، در حالی که صادرات نفت خام کشورهای عربی منطقه در هفته پایانی سپتامبر از سطح پیش از جنگ فراتر رفته است.

داده‌های کپلر نشان می‌دهد میانگین صادرات نفت خام منطقه در سپتامبر ۱۶.۵ میلیون بشکه در رو...

  ![Media](media/2026-10-02/f95f35f5c77f5254.jpg)
- **`@IranintlTV (ایران اینترنشنال (تلگرام))`** [دونالد ترامپ، رییس‌جمهوری آمریکا، پنج‌شنبه شب در تگزاس گفت جنگ با جمهوری اسلامی «خیلی زود» پایان خواهد یافت و تهران باید...](https://t.me/IranintlTV/360251) — `03:12 IRST` / `23:42 UTC`
  > دونالد ترامپ، رییس‌جمهوری آمریکا، پنج‌شنبه شب در تگزاس گفت جنگ با جمهوری اسلامی «خیلی زود» پایان خواهد یافت و تهران باید «تصمیم درست و هوشمندانه‌ای» بگیرد، در غیر این صورت موقعیت کنونی خود را از دست خواهد داد.

ترامپ با اشاره به شعار «مرگ بر آمریکا» گفت: «اینها آدم‌های دیوانه‌...

  ![Media](media/2026-10-02/f14136baccf1f854.jpg)
- **`@IranintlTV (ایران اینترنشنال (تلگرام))`** [اسکات بسنت، وزیر خزانه‌داری آمریکا، پنج‌شنبه نهم مهر گفت ایران در ماه سپتامبر هیچ نفت خامی در نفتکش‌ها بارگیری نکرده است...](https://t.me/IranintlTV/360250) — `03:01 IRST` / `23:31 UTC`
  > اسکات بسنت، وزیر خزانه‌داری آمریکا، پنج‌شنبه نهم مهر گفت ایران در ماه سپتامبر هیچ نفت خامی در نفتکش‌ها بارگیری نکرده است و این موضوع را نتیجه کارزار فشار دولت دونالد ترامپ، رییس‌جمهوری آمریکا، برای قطع یکی از منابع اصلی درآمد جمهوری اسلامی دانست.

بسنت در شبکه اجتماعی ایکس نوش...

  ![Media](media/2026-10-02/65bd4fcb1852666a.jpg)
- **`@IranintlTV (ایران اینترنشنال (تلگرام))`** [برت اریکسون، کارشناس تحریم‌ها و مدیر شرکت آبسیدین ریسک ادوایزرز، به رویترز گفت آمریکا پس از تحت فشار قرار دادن ایران در ...](https://t.me/IranintlTV/360249) — `02:54 IRST` / `23:24 UTC`
  > برت اریکسون، کارشناس تحریم‌ها و مدیر شرکت آبسیدین ریسک ادوایزرز، به رویترز گفت آمریکا پس از تحت فشار قرار دادن ایران در دریا و افزایش انزوای آن در مسیرهای هوایی، اکنون «شریان‌های اقتصادی» این کشور در خشکی را محدود می‌کند.

او هشدار داد: «نمی‌توان اقتصادی را به این شکل خفه کرد،...

  ![Media](media/2026-10-02/da6fcb68d8d48e0d.jpg)
- **`Reuters Wire`** [New Mexico wants Meta to pay up to $40 billion in penalties after data privacy trial - Reuters](https://news.google.com/rss/articles/CBMiuwFBVV95cUxPejVnckU0ZWxSMDJ5V2d2WXZfa0ZTQ3ctRW9zQWRCMDZYVjhBZ3F0QTJSRVNuN3MzbTZyVzNCREJLclVDZmowNzZCRDV3UmtyblJQd3M4aWxFVXc0UkRwSzExSUh4cTVpdWZuYXItYTM1YWVrbFJzMnR0ZWR3b3A4NVZrbU9maVc3Z3NpNmg3YVpaOEk4OEx1a3VFQXQteEJ6T1NHRmxaX0JKQzZHRmE5emVDOFM3bGFFNVl3?oc=5) — `02:52 IRST` / `23:22 UTC`
  > New Mexico wants Meta to pay up to $40 billion in penalties after data privacy trial    Reuters
- **`@patt_channel_x (کانال پترنی‌ها)`** [آپدیت بزرگ PattNG در راهه ...](https://t.me/patt_channel_x/155) — `02:49 IRST` / `23:19 UTC`
- **`Hacker News`** [Butterflies use optical illusions to dodge predators](https://www.essex.ac.uk/news/2026/09/30/butterflies-use-optical-illusions-to-dodge-predators) — `02:45 IRST` / `23:15 UTC`
  > Article URL: https://www.essex.ac.uk/news/2026/09/30/butterflies-use-optical-illusions-to-dodge-predators 
 Comments URL: https://news.ycombinator.com/item?id=49928152 
 Points: 7 
 # Comments: 0
- **`@IranintlTV (ایران اینترنشنال (تلگرام))`** [۴۶ کشور در بیانیه‌ای مشترک در شورای حقوق بشر سازمان ملل، افزایش استفاده جمهوری اسلامی از مجازات اعدام را محکوم کردند و د...](https://t.me/IranintlTV/360248) — `02:43 IRST` / `23:13 UTC`
  > ۴۶ کشور در بیانیه‌ای مشترک در شورای حقوق بشر سازمان ملل، افزایش استفاده جمهوری اسلامی از مجازات اعدام را محکوم کردند و درباره اعدام معترضان و احکام اعدام مرتبط با اعتراضات و آزادی‌های اساسی ابراز نگرانی کردند. این بیانیه چهارشنبه هشتم مهر از سوی نماینده لیختن‌اشتاین قرائت شد.
...

  ![Media](media/2026-10-02/577fc2f1a2aa4248.jpg)
- **`Reuters Wire`** [Boeing white-collar workers approve contract offer, averting strike fears - Reuters](https://news.google.com/rss/articles/CBMi1AFBVV95cUxPd19DdEhGSTRqZC1hb0JqbmFsRHA5a2dQVXlIbkZ4MjJ6Q2FkSGV6RDdsWmtoMlRtQWkyc3NpNGZTRjJaUGFiTG04Vlk3bFZKN0FyM2pJVDlhbjIwcVdnbXpJb29rUkpXcEViVENySzJUdFhkZHRqXzJlZmlPbUgyd2dzVF9DbVRGN1ZpQzZGczRHUDM4T1QydUs5Rmxjb3VZaS1zU1ZsTC0zT05OcGJMMXk2U1dpT2ZUVWpjMG1nTDBKWi0tMzJqckpzZnJiSWxmd3FmWQ?oc=5) — `02:43 IRST` / `23:13 UTC`
  > Boeing white-collar workers approve contract offer, averting strike fears    Reuters
- **`Hacker News`** [Several vulnerabilities have been discovered in the Linux kernel](https://lwn.net/Articles/1097401/) — `02:40 IRST` / `23:10 UTC`
  > Article URL: https://lwn.net/Articles/1097401/ 
 Comments URL: https://news.ycombinator.com/item?id=49928121 
 Points: 32 
 # Comments: 5

---

## 🗄 آرشیو بولتن‌های ۳۰ دقیقه‌ای (Interval Archive)

- 📅 [2026-10-02 - ساعت 00:30](news/2026-10-02/00-30.md)
- 📅 [2026-10-01 - ساعت 20:30](news/2026-10-01/20-30.md)
- 📅 [2026-10-01 - ساعت 15:00](news/2026-10-01/15-00.md)
- 📅 [2026-10-01 - ساعت 07:00](news/2026-10-01/07-00.md)
- 📅 [2026-10-01 - ساعت 00:00](news/2026-10-01/00-00.md)
- 📅 [2026-09-30 - ساعت 20:30](news/2026-09-30/20-30.md)
- 📅 [2026-09-30 - ساعت 15:30](news/2026-09-30/15-30.md)
- 📅 [2026-09-30 - ساعت 08:00](news/2026-09-30/08-00.md)
- 📅 [2026-09-30 - ساعت 01:30](news/2026-09-30/01-30.md)
- 📅 [2026-09-29 - ساعت 22:00](news/2026-09-29/22-00.md)

---
توسعه‌یافته برای استقرار سبک و مداوم بر روی اوبونتو ARM64.
