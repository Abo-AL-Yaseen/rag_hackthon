"""Conservative academic intent and context decisions; never stores academic facts."""
import re
import unicodedata


def normalize(text):
    text = ''.join(str(unicodedata.decimal(c)) if c.isdecimal() else c
                   for c in unicodedata.normalize('NFKC', text))
    text = re.sub(r'[\u064b-\u065f\u0670\u0640]', '', text.lower())
    return text.translate(str.maketrans('أإآىة', 'ااايه'))


def intent(question):
    q = normalize(question)
    if re.search(r'قصيده|شعر|poem|joke|نكته', q): return 'out_of_scope'
    if re.search(r'كم\s+(?:تخصص|برنامج)|عدد.{0,20}(?:تخصص|برامج)|اسماء.{0,20}(?:تخصص|برامج)|'
                 r'(?:تخصصات|برامج).{0,25}(?:متوفر|متاح|موجود)|'
                 r'what.{0,20}engineering programs|how many\s+(?:engineering\s+)?programs|'
                 r'(?:engineering\s+)?programs.{0,20}(?:available|listed|offered)', q): return 'catalog'
    if re.search(r'امتحان|exam', q) and re.search(r'موعد|متي|ايمت|الاسبوع|القادم|schedule|when|next', q): return 'schedule'
    if re.search(r'انذار|ينذر|warning|probation', q): return 'warning'
    if re.search(r'غياب|غبت|اغيب|غاب|تغيب|غيبت|حضور|دوام|داوم|absen|attendan|miss.{0,15}class', q): return 'attendance'
    if re.search(r'(?:مواد|مساقات).{0,45}(?:هندسه|تخصص|خطه|السنه)|(?:اعطيني|اعرض|قائمه|كل|جميع).{0,25}(?:مواد|مساقات)|(?:list|show|all).{0,55}(?:courses|study plan)',q):return 'course_list'
    if re.search(r'اضافه.{0,20}(?:مساق|مواد|ماده)|add.{0,20}course', q): return 'add_drop'
    if re.search(r'سحب|اسحب|انسح|withdraw|drop', q):
        return 'add_drop' if re.search(r'اضاف|بدايه|بداي|add|beginning|start', q) and not re.search(r'مالي|financial|refund', q) else 'withdrawal'
    if re.search(r'تخرج|graduat', q) and re.search(r'ساع|مجموع|معتمد|credit|hour|total', q): return 'graduation'
    if re.search(r'ساع|credit|hour', q) and re.search(r'اسجل|انزل|سجل|register|enrol|take', q) and not re.search(r'\d{6,10}', q): return 'load'
    if re.search(r'\d{6,10}', q): return 'course'
    if re.search(r'متطلب|prereq|co.?requis', q): return 'course'
    if re.search(r'مساق|ماده|course', q) and re.search(r'ساع|credit|hour', q): return 'course'
    if re.search(r'كم.{0,25}ساع|قديش.{0,25}ساع|how many.{0,25}(?:credits|hours)', q): return 'course'
    return 'unknown'


MESSAGES = {
 'language_evidence': {'ar':'الأدلة المسترجعة لا تتوفر بالعربية. لا أستطيع ترجمتها كإجابة أكاديمية موثقة في الوضع المحلي. اختر لغة المصدر أو راجع القسم.',
                      'en':'The retrieved evidence is not available in English. Local extractive mode cannot provide a verified English translation. Please select the source language or contact the department.'},
 'scope': {'ar':'عشان أعطيك المعلومة الصحيحة، اختار تخصصك ونسخة خطتك الدراسية؛ معلومات المساقات ومتطلبات التخرج ممكن تختلف من خطة لثانية.',
           'en':'Please select your program and study-plan version so I can use the correct course or graduation requirements.'},
 'conflict': {'ar':'التخصص أو نسخة الخطة في سؤالك لا يتطابق مع الاختيار الحالي. وضّح أي تخصص وخطة تريد اعتمادها.',
              'en':'The program or plan mentioned in your question conflicts with the selected context. Please clarify which to use.'},
 'warning': {'ar':'عشان أحدد قاعدة الإنذار المناسبة، وضّح كليتك وفصل التحاقك، وهل هذا أول فصل إلك بالجامعة.',
             'en':'Please clarify your faculty, admission semester, and whether this is your first semester so I can identify the applicable warning rule.'},
 'load': {'ar':'هل تقصد الفصل العادي أو الصيفي، وهل تخرجك متوقف على الساعات المطلوبة؟ ما عندي وصول لسجلك الشخصي لتحديد أهليتك.',
          'en':'Is this a regular or summer semester, and are these credits needed to graduate? I cannot access your personal academic record to determine eligibility.'},
 'schedule': {'ar':'ما عندي جدول امتحانات موثوق في المستندات المتاحة. راجع جدول الامتحانات الرسمي أو دائرة القبول والتسجيل.',
              'en':'The available documents do not include a verified exam schedule. Please check the official schedule or Admissions and Registration.'},
 'missing': {'ar':'ما لقيت معلومات موثوقة عن هذا المساق في الخطة الدراسية المتاحة عندي. تأكد من رمز المساق، أو راجع القسم الأكاديمي.',
             'en':'I could not find verified information about this course in the selected study plan. Please check its code or contact the department.'},
 'out_of_scope': {'ar':'بقدر أساعدك باللوائح الأكاديمية والخطط الدراسية الهندسية المتاحة. سؤالك خارج نطاق المرشد الأكاديمي.',
                  'en':'I can help with the available academic regulations and Engineering study plans. This request is outside the academic advisor’s scope.'},
}


def program_mentions(question, programs):
    def tokens(text):
        return ' '.join(t[2:] if t.startswith('ال') and len(t)>4 else t
                        for t in re.findall(r'[\w]+', normalize(text)))
    q = ' '+tokens(question)+' '
    matches = []
    for program in programs:
        for name in (program.get('name_ar'), program.get('name_en')):
            if name and (' '+tokens(name)+' ') in q:
                matches.append((program['program_id'], tokens(name)))
    # A verified longer program name can contain another verified name.
    return {p for p,n in matches if not any(n != other and n in other for _,other in matches)}
