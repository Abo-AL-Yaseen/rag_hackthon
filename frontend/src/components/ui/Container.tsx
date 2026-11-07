import type { ReactNode } from 'react'

type Props = {
  children: ReactNode
  className?: string
  as?: 'div' | 'section' | 'header' | 'footer'
}

export function Container({ children, className = '', as: Tag = 'div' }: Props) {
  return (
    <Tag className={`mx-auto w-full max-w-[1240px] px-4 sm:px-6 lg:px-8 ${className}`}>
      {children}
    </Tag>
  )
}
