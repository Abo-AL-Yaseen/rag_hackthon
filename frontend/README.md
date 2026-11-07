# المرشد الأكاديمي الذكي — Frontend

واجهة عربية (RTL) لمنصة المساعدة الأكاديمية المرتبطة بمشروع IEEE RAG Hackathon.

## Stack

- React + Vite + TypeScript
- Tailwind CSS v4 (`@tailwindcss/vite`)
- Lucide React
- Motion (`motion/react`)
- React Router

## تشغيل محلي

```bash
cd frontend
npm install
npm run dev
```

العنوان الافتراضي: [http://localhost:5173](http://localhost:5173)

```bash
npm run build
```

## الصفحات الحالية

- `/` الصفحة الرئيسية
- `/advisor` واجهة انتقال مؤقتة للمرشد (بدون استدعاء LLM)

إرسال سؤال من شريط البحث ينقل إلى `/advisor` مع حفظ نص السؤال في `location.state`.

## ملاحظات تكامل RAG

عقد الاستجابة v1.0.0 موثّق في `docs/` بجذر المستودع. ملفات mock موجودة في `src/mocks/` للاستخدام لاحقًا عند ربط Backend.
