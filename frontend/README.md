# المرشد الأكاديمي — واجهة الهندسة المتكاملة

واجهة React/Vite/TypeScript عربية مع تصميم الفريق الأصلي، متصلة بخلفية FastAPI المحلية.

```powershell
# From D:\rag_hackathon; Backend must already be running separately.
.\scripts\run_final_demo.ps1 -Component frontend
```

Or from frontend/: `npm.cmd run dev -- --host 127.0.0.1 --port 5173 --strictPort`. Default Vite proxies /api and /health to127.0.0.1:8000. Optional VITE_API_BASE_URL selects an explicit Backend origin. Never put server keys into VITE_*.

`npm.cmd run build` checks TypeScript and builds. `npm.cmd run lint` runs Oxlint. `npm.cmd run test:store` uses Node22 built-in TypeScript stripping to test asynchronous request state, chat switching/deletion, scope changes and API failures; it is not a rendered-browser test.

Home `/` and advisor `/advisor` preserve Arabic styling/RTL. Choose a program and its published plan, or general regulations without a program. Names/versions come from /api/programs. Context changes create another conversation and retain the previous one. Delayed replies update only their captured conversation. All responses preserve status/reason/mode/source fields and are rendered as escaped text with source cards.

The current Backend is deliberately mock-only. The UI prominently labels simulation, loading, insufficient evidence and unavailable/error states. Only registered verified example questions have scripted answers; other questions may refuse. Previous demo-only chats are left in the old browser storage key and are not imported as real answers.
