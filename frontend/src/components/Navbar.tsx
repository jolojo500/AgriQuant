import { NavLink } from 'react-router-dom'

const links = [
  { to: '/globe',  label: 'Globe'  },
  { to: '/stocks', label: 'Stocks' },
  { to: '/model',  label: 'Model'  },
]

export default function Navbar() {
  return (
    <nav style={{
      position: 'fixed',
      top: 0, left: 0, right: 0,
      height: 'var(--navbar-h)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'space-between',
      padding: '0 2rem',
      background: 'rgba(5, 8, 15, 0.85)',
      backdropFilter: 'blur(12px)',
      borderBottom: '1px solid var(--border)',
      zIndex: 100,
    }}>
      <NavLink to="/" style={{ textDecoration: 'none' }}>
        <span style={{
          fontFamily: 'var(--font-display)',
          fontSize: '1.1rem',
          color: 'var(--green)',
        }}>
          AGRI<span style={{ color: 'var(--text-primary)' }}>QUANT</span>
        </span>
      </NavLink>

      <div style={{ display: 'flex', gap: '2rem' }}>
        {links.map(({ to, label }) => (
          <NavLink
            key={to}
            to={to}
            
            style={({ isActive }) => ({
              fontFamily: 'var(--font-display)',
              fontSize: '0.8rem',
              textDecoration: 'none',
              color: isActive ? 'var(--text-primary)' : 'var(--text-secondary)',
              borderBottom: isActive ? '1px solid var(--green)' : '1px solid transparent',
              paddingBottom: '2px',
              transition: 'color 0.2s',
              //fontWeight: 700,
              //textTransform: 'uppercase' as const,
              //letterSpacing: '0.1em'
            })}
          >
            {label}
          </NavLink>
        ))}
      </div>
    </nav>
  )
}