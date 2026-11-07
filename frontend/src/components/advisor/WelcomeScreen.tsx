import { Sparkles } from 'lucide-react'
import { RobotIllustration } from './RobotIllustration'
import { SuggestedQuestions, type SuggestionItem } from './SuggestedQuestions'

type Props = {
  suggestions: SuggestionItem[]
  onSelectSuggestion: (text: string) => void
}

export function WelcomeScreen({ suggestions, onSelectSuggestion }: Props) {
  return (
    <div className="advisor-welcome">
      <div className="advisor-welcome__hero">
        <RobotIllustration />
        <div className="advisor-welcome__copy">
          <p className="advisor-welcome__eyebrow">
            <Sparkles className="h-4 w-4" strokeWidth={2} aria-hidden="true" />
            مرحبًا بك في
          </p>
          <h2 className="advisor-welcome__title">
            المرشد الأكاديمي <span className="advisor-welcome__title-accent">الذكي</span>
          </h2>
          <p className="advisor-welcome__desc">
            اسأل عن خطط كلية الهندسة ومساقاتها والأنظمة الجامعية المتاحة.
            اختر تخصصك ونسخة خطتك أولاً؛ عند غياب الدليل سنوضح ذلك.
          </p>
        </div>
      </div>

      <SuggestedQuestions items={suggestions} onSelect={onSelectSuggestion} />
    </div>
  )
}
