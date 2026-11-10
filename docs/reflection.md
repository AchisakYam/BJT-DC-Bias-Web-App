# Reflection — Lab 02

## 1. ทำไมการเปิด `templates/index.html` ตรง ๆ จึงไม่เท่ากับการรัน Flask?

เพราะไฟล์นั้นเป็น **Jinja template** ไม่ใช่หน้าเว็บที่สมบูรณ์ เมื่อเปิดด้วย `file://`
จะเกิดสามปัญหา:

1. `{{ ... }}` และ `{% ... %}` ไม่ถูกประมวลผล — ผู้ใช้จะเห็นโค้ด template ดิบ ๆ
   แทนที่จะเห็นค่าตัวเลข
2. ไม่มี HTTP request ไปถึง Python เลย จึงไม่มี `parse_form` / `calculate` ทำงาน
   ตัวเลข DC Bias ทั้งหมดมาจาก backend ไม่ใช่จาก HTML
3. `url_for(...)` (path ของ CSS และ action ของฟอร์ม) ต้องอาศัย Flask routing
   ถ้าไม่มี server จะได้ path ที่ใช้งานไม่ได้ และเมื่อกด Submit ฟอร์มก็ไม่มีใครรับ

สรุป: `file://` ได้แค่ "ไฟล์ข้อความ" ส่วน Flask ทำหน้าที่เป็น server ที่รับ request,
เรียก Python คำนวณ แล้วค่อย render template กลับมาเป็น HTML จริงให้ browser

## 2. ฟอร์มส่งข้อมูลไป Python อย่างไร?

1. ฟอร์มมี `method="post"` และ `action="{{ url_for('calculate_bias') }}"` → `/calculate`
2. เมื่อกด **Calculate DC Bias** browser รวบรวมค่าจาก `<input name="...">` ทั้ง 7 ตัว
   (`vcc, r1, r2, rc, re, beta, vbe`) แล้วเข้ารหัสเป็น
   `application/x-www-form-urlencoded` ส่งเป็น HTTP POST
3. Flask จับคู่ route `/calculate` แล้วเรียกฟังก์ชัน `calculate_bias()`
4. ฟังก์ชันอ่านค่าด้วย `request.form.get(...)` ส่งเข้า `dc_bias.parse_form()`
   (ตรวจสอบ + แปลง kΩ → Ω) แล้วเรียก `dc_bias.calculate()` เพื่อคำนวณ
5. Flask ส่ง `BiasResult` ให้ Jinja render กลับเป็น HTML response (HTTP 200)

ถ้าค่าไม่ถูกต้อง `parse_form` โยน `ValidationError` แล้ว route จะ render หน้าเดิม
พร้อมข้อความ error โดยไม่คำนวณและไม่ทำให้เว็บล้ม

## 3. ถ้าแก้สมการใน `dc_bias.py` ต้องแก้ HTML หรือไม่?

**ไม่ต้อง** ตราบใดที่ยังคืนค่า `BiasResult` ที่มีฟิลด์เดิม (`vb, ve, vc, vce, ib, ic, ie, vth, rth`)
เพราะ HTML ทำหน้าที่แค่ *แสดง* ค่าที่ได้รับมา ไม่ได้รู้จักสมการเลย

แต่ถ้าเพิ่มฟิลด์ใหม่ (เช่น `vbc`) หรือเปลี่ยนหน่วยที่คืนค่า ต้องแก้ทั้ง template
และเทสต์ด้วย — นี่คือเหตุผลที่เรามี `test_dc_bias.py` ตรึงค่าตัวเลข และ `test_web.py`
ตรึงค่าที่แสดงบนหน้าเว็บ ถ้าแก้สมการแล้วผลเปลี่ยน เทสต์จะฟ้องทันที

## 4. ทำไมผลใน Region ที่แบบจำลองใช้ไม่ได้จึงต้องมี Warning?

เพราะสมการที่ใช้ (`IB = (VTH − VBE)/(RTH + (β+1)RE)` ฯลฯ) ตั้งอยู่บนสมมติฐาน
**Forward-Active** เท่านั้น คือรอยต่อ B-E forward bias และ B-C reverse bias

- **Cutoff** (`VTH ≤ VBE`): ทรานซิสเตอร์ไม่นำกระแส สมการจะให้ IB ติดลบ/ศูนย์
  ซึ่งไม่มีความหมายทางกายภาพ
- **Saturation** (`VCE ≤ 0.3 V`): รอยต่อ B-C กลายเป็น forward bias กระแส Collector
  ไม่ได้เป็น β เท่าของ IB อีกต่อไป ตัวเลขที่คำนวณได้จึงเชื่อถือไม่ได้

ถ้าเว็บแสดงตัวเลขพวกนี้เหมือนกรณี Active ผู้ใช้อาจนำไปออกแบบวงจรผิดโดยไม่รู้ตัว
การแสดง Region + Warning จึงเป็นการบอก **ขอบเขตความใช้ได้ของแบบจำลอง**
ซึ่งเป็นส่วนหนึ่งของงานวิศวกรรม ไม่ใช่แค่การตกแต่งหน้าเว็บ
