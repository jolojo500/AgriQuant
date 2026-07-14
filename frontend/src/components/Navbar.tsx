import { NavLink } from 'react-router-dom'

const links = [
  { to: '/globe',  label: 'Globe'  },
  { to: '/stocks', label: 'Stocks' },
  { to: '/model',  label: 'Model'  },
]

export default function Navbar() {
  return (
    <nav className="fixed inset-x-0 top-0 z-[100] flex h-14 items-center justify-between border-b border-line bg-canvas/85 px-8 backdrop-blur-md">
      <NavLink to="/" className="no-underline">
        <span className="font-display text-[1.1rem] text-accent">
          AGRI<span className="text-ink">QUANT</span>
        </span>
      </NavLink>

      <div className="flex gap-8">
        {links.map(({ to, label }) => (
          <NavLink
            key={to}
            to={to}
            className={({ isActive }) =>
              `font-display text-[0.8rem] no-underline pb-0.5 border-b transition-colors duration-200 ${
                isActive ? 'text-ink border-accent' : 'text-ink-muted border-transparent'
              }`
            }
          >
            {label}
          </NavLink>
        ))}
      </div>
    </nav>
  )
}
