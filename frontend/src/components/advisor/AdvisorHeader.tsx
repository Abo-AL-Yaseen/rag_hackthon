import { GraduationCap, Menu, UserRound } from 'lucide-react'

type Props = {
  onToggleSidebar: () => void
}

export function AdvisorHeader({ onToggleSidebar }: Props) {
  return (
    <header className="advisor-header" role="banner">
      <div className="advisor-header__brand">
        <button
          type="button"
          className="advisor-header__menu"
          onClick={onToggleSidebar}
          aria-label="فتح القائمة الجانبية"
        >
          <Menu className="h-5 w-5" aria-hidden="true" />
        </button>
        <div className="advisor-header__logo" aria-hidden="true">
          <GraduationCap className="h-6 w-6 text-white" strokeWidth={1.8} />
        </div>
        <div className="advisor-header__titles">
          <h1 className="advisor-header__title">المرشد الأكاديمي الذكي</h1>
          <p className="advisor-header__subtitle">جامعة النجاح الوطنية</p>
        </div>
      </div>

      <div className="advisor-header__actions">
        <button type="button" className="advisor-header__login">
          تسجيل الدخول
        </button>
        <button type="button" className="advisor-header__user" aria-label="حساب المستخدم">
          <UserRound className="h-5 w-5" strokeWidth={1.7} aria-hidden="true" />
        </button>
      </div>
    </header>
  )
}
