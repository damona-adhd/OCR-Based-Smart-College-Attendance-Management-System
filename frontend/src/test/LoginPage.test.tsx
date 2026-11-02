import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { Toaster } from 'react-hot-toast'
import { vi } from 'vitest'
import LoginPage from '../pages/auth/LoginPage'
import { AuthProvider } from '../features/auth/AuthContext'
import * as authApi from '../api/auth'

vi.mock('../api/auth', () => ({
  authApi: {
    login: vi.fn(),
    me: vi.fn(),
  },
}))

function renderLogin() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter>
        <AuthProvider>
          <LoginPage />
          <Toaster />
        </AuthProvider>
      </MemoryRouter>
    </QueryClientProvider>
  )
}

describe('LoginPage - Three Role Cards', () => {
  beforeEach(() => {
    localStorage.clear()
    vi.clearAllMocks()
  })

  it('renders all three mandatory role cards on initial landing', () => {
    renderLogin()
    expect(screen.getByText('Administrator')).toBeInTheDocument()
    expect(screen.getByText('Teacher')).toBeInTheDocument()
    expect(screen.getByText('Student')).toBeInTheDocument()
    expect(screen.getByText('Continue as Administrator')).toBeInTheDocument()
    expect(screen.getByText('Continue as Teacher')).toBeInTheDocument()
    expect(screen.getByText('Continue as Student')).toBeInTheDocument()
  })

  it('opens role-specific login form when card is clicked and allows going back', () => {
    renderLogin()
    // Click Continue as Administrator
    fireEvent.click(screen.getByText('Continue as Administrator'))

    expect(screen.getByText('Administrator Login')).toBeInTheDocument()
    expect(screen.getByLabelText(/username or admin id/i)).toBeInTheDocument()
    expect(screen.getByPlaceholderText(/enter your account password/i)).toBeInTheDocument()
    expect(screen.getByText('Back to Role Selection')).toBeInTheDocument()

    // Click Back
    fireEvent.click(screen.getByText('Back to Role Selection'))
    expect(screen.getByText('Continue as Administrator')).toBeInTheDocument()
  })

  it('shows validation errors when fields are empty in role form', async () => {
    renderLogin()
    fireEvent.click(screen.getByText('Continue as Teacher'))
    fireEvent.click(screen.getByRole('button', { name: /sign in as teacher/i }))

    await waitFor(() => {
      expect(screen.getByText(/username or usn is required/i)).toBeInTheDocument()
    })
  })

  it('calls login API with credentials and role selection', async () => {
    const mockLogin = vi.spyOn(authApi.authApi, 'login').mockResolvedValue({
      access_token: 'tok',
      refresh_token: 'rtok',
      token_type: 'bearer',
      role: 'admin',
      user_id: 1,
      username: 'admin',
    })
    vi.spyOn(authApi.authApi, 'me').mockResolvedValue({
      id: 1,
      username: 'admin',
      email: 'admin@college.edu',
      role: 'admin',
      is_active: true,
    })

    renderLogin()
    fireEvent.click(screen.getByText('Continue as Administrator'))

    fireEvent.change(screen.getByLabelText(/username/i), { target: { value: 'admin' } })
    fireEvent.change(screen.getByPlaceholderText(/enter your account password/i), { target: { value: 'pass' } })
    fireEvent.click(screen.getByRole('button', { name: /sign in as administrator/i }))

    await waitFor(() => expect(mockLogin).toHaveBeenCalledWith('admin', 'pass', 'admin'))
  })
})
