export const siteMeta = {
  projectName: 'المرشد الطلابي الذكي',
  universityName: 'جامعة النجاح الوطنية',
  tagline: 'دليلك الذكي في جامعة النجاح الوطنية',
  description:
    'مساعد يعتمد على الذكاء الاصطناعي للإجابة عن كل ما يتعلق بالتخصصات، الخطط الدراسية، المساقات، والمتطلبات.',
  disclaimer:
    'المنصة مشروع مساعد أكاديمي، ولا تُغني إجاباته عن الرجوع إلى الإعلانات والتعليمات الرسمية للجامعة.',
  officialSite: 'https://www.najah.edu/ar/',
}

export const navLinks = [
  { id: 'home', label: 'الرئيسية', to: '/', active: true },
  { id: 'advisor', label: 'المرشد الذكي', to: '/advisor' },
  { id: 'library', label: 'المكتبة الأكاديمية', to: '/library', soon: true },
  { id: 'plans', label: 'الخطط الدراسية', to: '/plans', soon: true },
  { id: 'faq', label: 'الأسئلة الشائعة', to: '/faq', soon: true },
] as const

export const searchSuggestions = [
  {
    id: 'marketing',
    label: 'ما هي متطلبات تخصص التسويق؟',
    icon: 'graduation' as const,
  },
  {
    id: 'prereq',
    label: 'ما المتطلب السابق لمساق BUS230؟',
    icon: 'book' as const,
  },
  {
    id: 'cs-hours',
    label: 'كم ساعة تخصص علوم الحاسوب؟',
    icon: 'clock' as const,
  },
]

export const featureStrip = [
  {
    id: 'instant',
    title: 'إجابات فورية ودقيقة',
    description: 'احصل على ردود واضحة خلال ثوانٍ لاستفساراتك الأكاديمية.',
    icon: 'zap' as const,
    tone: 'purple' as const,
  },
  {
    id: 'official',
    title: 'معلومات محدثة من الخطط الرسمية',
    description: 'يعتمد على مصادر وخطط دراسية معتمدة من الجامعة.',
    icon: 'layers' as const,
    tone: 'blue' as const,
  },
  {
    id: 'coverage',
    title: 'يغطي جميع تخصصات الجامعة',
    description: 'دعم واسع للتخصصات والمساقات والمتطلبات السابقة.',
    icon: 'target' as const,
    tone: 'teal' as const,
  },
  {
    id: 'always',
    title: 'متاح على مدار الساعة 24/7',
    description: 'مساعد أكاديمي جاهز في أي وقت ومن أي جهاز.',
    icon: 'clock' as const,
    tone: 'violet' as const,
  },
]

export const exploreTopics = [
  {
    id: 'majors',
    title: 'التخصصات والخطط',
    description: 'استعرض التخصصات الجامعية والخطط الدراسية والمساقات والمتطلبات.',
    icon: 'graduation',
    tone: 'purple',
    to: '/plans',
  },
  {
    id: 'courses',
    title: 'المساقات',
    description: 'ابحث عن المساقات ورموزها وساعاتها ومتطلباتها السابقة.',
    icon: 'book',
    tone: 'blue',
    to: '/library',
  },
  {
    id: 'services',
    title: 'الخدمات الطلابية',
    description: 'تعرّف على الخدمات والإجراءات الأكاديمية والإدارية.',
    icon: 'layers',
    tone: 'mint',
    to: '/services',
  },
  {
    id: 'admission',
    title: 'التسجيل والقبول',
    description: 'معلومات القبول والتسجيل والتقويم الأكاديمي.',
    icon: 'clipboard',
    tone: 'violet',
    to: '/admission',
  },
] as const

export const quickTools = [
  {
    id: 'favorites',
    title: 'مساقاتي المفضلة',
    description: 'احفظ المساقات المهمة للرجوع إليها لاحقًا.',
    icon: 'star',
    to: '/tools/favorites',
  },
  {
    id: 'plan',
    title: 'خطتي الدراسية',
    description: 'تابع مسارك الدراسي وتنظيم المتطلبات.',
    icon: 'calendar',
    to: '/plans',
  },
  {
    id: 'gpa',
    title: 'حاسبة المعدل',
    description: 'أداة حساب المعدل ستتوفر في إصدار لاحق.',
    icon: 'calculator',
    to: '/tools/gpa',
  },
  {
    id: 'calendar',
    title: 'التقويم الأكاديمي',
    description: 'مواعيد هامة مرتبطة بالفصل الدراسي.',
    icon: 'bell',
    to: '/tools/calendar',
  },
] as const

export const benefits = [
  {
    id: 'arabic',
    title: 'البحث باللغة العربية',
    description: 'واجهة عربية كاملة مع دعم اتجاه الكتابة من اليمين إلى اليسار.',
    icon: 'languages',
  },
  {
    id: 'courses-info',
    title: 'الوصول إلى معلومات المساقات',
    description: 'استفسارات منظمة حول المساقات والمتطلبات والخطط الدراسية.',
    icon: 'book-open',
  },
  {
    id: 'organized',
    title: 'تنظيم المعلومات الأكاديمية',
    description: 'عرض الإجابات والمصادر بطريقة واضحة تساعد على اتخاذ القرار.',
    icon: 'layout',
  },
] as const

export const footerGroups = [
  {
    title: 'صفحات المنصة',
    links: [
      { label: 'الرئيسية', to: '/' },
      { label: 'المرشد الذكي', to: '/advisor' },
      { label: 'المكتبة الأكاديمية', to: '/library' },
      { label: 'الخطط الدراسية', to: '/plans' },
    ],
  },
  {
    title: 'الخدمات',
    links: [
      { label: 'التخصصات والخطط', to: '/plans' },
      { label: 'المساقات', to: '/library' },
      { label: 'الخدمات الطلابية', to: '/services' },
      { label: 'التسجيل والقبول', to: '/admission' },
    ],
  },
] as const
