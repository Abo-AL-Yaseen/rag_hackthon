import { exploreTopics } from '../../data/homeContent'
import { Container } from '../ui/Container'
import { SectionHeading } from '../ui/SectionHeading'
import { TopicCard } from './TopicCard'

export function ExploreSection() {
  return (
    <section id="explore" className="bg-[var(--background)] py-8 sm:py-12">
      <Container>
        <SectionHeading
          eyebrow="اكتشف الجامعة"
          title="كل ما تحتاجه في مكان واحد"
          description="استكشف أهم المواضيع والخدمات الأكاديمية بطريقة أسهل وأسرع."
        />
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
          {exploreTopics.map((topic, index) => (
            <TopicCard key={topic.id} {...topic} index={index} />
          ))}
        </div>
      </Container>
    </section>
  )
}
