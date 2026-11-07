import type { ButtonHTMLAttributes, ReactNode } from 'react'
import { Link } from 'react-router-dom'

type Shared = {
  children: ReactNode
  className?: string
  icon?: ReactNode
}

type ButtonProps = Shared &
  ButtonHTMLAttributes<HTMLButtonElement> & {
    to?: undefined
  }

type LinkProps = Shared & {
  to: string
  state?: unknown
  onClick?: () => void
}

function buttonClasses(extra = '') {
  return `inline-flex items-center justify-center gap-2 rounded-full bg-[linear-gradient(120deg,#7547ed,#5b6cff)] px-5 py-2.5 text-sm font-semibold text-white shadow-[0_12px_30px_rgba(117,71,237,0.35)] transition hover:brightness-110 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--purple-light)] disabled:cursor-not-allowed disabled:opacity-60 ${extra}`
}

export function GradientButton(props: ButtonProps | LinkProps) {
  if ('to' in props && props.to) {
    return (
      <Link to={props.to} state={props.state} onClick={props.onClick} className={buttonClasses(props.className)}>
        {props.children}
        {props.icon}
      </Link>
    )
  }

  const { children, icon, className, to: _to, ...rest } = props as ButtonProps & { to?: undefined }
  void _to
  return (
    <button type="button" className={buttonClasses(className)} {...rest}>
      {children}
      {icon}
    </button>
  )
}
