import { motion, useReducedMotion } from 'motion/react'

const HERO_NAVY = '#101634'

export function HeroIllustration() {
  const reduceMotion = useReducedMotion()

  return (
    <div className="relative mx-auto flex w-full max-w-[440px] items-center justify-center lg:max-w-none">
      <div
        className="pointer-events-none absolute inset-[10%] rounded-full bg-[radial-gradient(circle,rgba(117,71,237,0.22)_0%,rgba(69,109,255,0.1)_42%,transparent_70%)] blur-2xl"
        aria-hidden="true"
      />

      <motion.div
        className="relative z-10 w-full overflow-hidden rounded-[28px]"
        style={{ backgroundColor: HERO_NAVY }}
        animate={reduceMotion ? undefined : { y: [0, -10, 0] }}
        transition={{ duration: 5.5, repeat: Infinity, ease: 'easeInOut' }}
      >
        <img
          src="/assets/advisor-robot-navy.png"
          alt="المساعد الذكي لجامعة النجاح"
          className="relative z-10 mx-auto block h-auto w-full max-w-[400px] object-contain object-center select-none"
          draggable={false}
          width={1024}
          height={1024}
        />
      </motion.div>
    </div>
  )
}
