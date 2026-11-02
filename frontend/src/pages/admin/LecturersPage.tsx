import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Plus, UserX } from 'lucide-react'
import toast from 'react-hot-toast'
import { PageHeader } from '../../components/ui/PageHeader'
import { Modal } from '../../components/ui/Modal'
import { ConfirmDialog } from '../../components/ui/ConfirmDialog'
import { EmptyState } from '../../components/ui/EmptyState'
import { Spinner } from '../../components/ui/Spinner'
import { lecturersApi } from '../../api/lecturers'
import { departmentsApi } from '../../api/departments'

function LecturerForm({ depts, onSave, onClose }: any) {
  const [form, setForm] = useState({ employee_id: '', full_name: '', department_id: '', username: '', email: '', password: '' })
  const set = (k: string) => (e: any) => setForm(f => ({ ...f, [k]: e.target.value }))
  return (
    <form onSubmit={e => { e.preventDefault(); onSave({ ...form, department_id: Number(form.department_id) }) }} className="space-y-4">
      <div className="grid grid-cols-2 gap-4">
        <div><label className="label">Employee ID</label><input className="input" value={form.employee_id} onChange={set('employee_id')} required placeholder="EMP001" /></div>
        <div><label className="label">Full Name</label><input className="input" value={form.full_name} onChange={set('full_name')} required /></div>
        <div><label className="label">Department</label><select className="input" value={form.department_id} onChange={set('department_id')} required><option value="">Select</option>{depts.map((d:any)=><option key={d.id} value={d.id}>{d.name}</option>)}</select></div>
        <div><label className="label">Username</label><input className="input" value={form.username} onChange={set('username')} required /></div>
        <div><label className="label">Email</label><input className="input" type="email" value={form.email} onChange={set('email')} required /></div>
        <div><label className="label">Password</label><input className="input" type="password" value={form.password} onChange={set('password')} required minLength={8} /></div>
      </div>
      <div className="flex gap-3 justify-end pt-2">
        <button type="button" className="btn-secondary" onClick={onClose}>Cancel</button>
        <button type="submit" className="btn-primary">Create Lecturer</button>
      </div>
    </form>
  )
}

export default function LecturersPage() {
  const qc = useQueryClient()
  const [showCreate, setShowCreate] = useState(false)
  const [deactivateId, setDeactivateId] = useState<number | null>(null)

  const { data: lecturers = [], isLoading } = useQuery({ queryKey: ['lecturers'], queryFn: () => lecturersApi.list() })
  const { data: depts = [] } = useQuery({ queryKey: ['departments'], queryFn: () => departmentsApi.list() })

  const createMut = useMutation({
    mutationFn: lecturersApi.create,
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['lecturers'] }); toast.success('Lecturer created'); setShowCreate(false) },
    onError: (e: any) => toast.error(e.response?.data?.detail || 'Failed'),
  })
  const deactivateMut = useMutation({
    mutationFn: lecturersApi.deactivate,
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['lecturers'] }); toast.success('Deactivated'); setDeactivateId(null) },
  })

  return (
    <div>
      <PageHeader title="Lecturers" actions={
        <button className="btn-primary" onClick={() => setShowCreate(true)}><Plus size={16} />Add Lecturer</button>
      } />

      {isLoading ? <div className="flex justify-center py-16"><Spinner size="lg" /></div> :
       lecturers.length === 0 ? <EmptyState title="No lecturers yet" /> : (
        <div className="card p-0 overflow-hidden">
          <table className="w-full">
            <thead className="bg-gray-50 border-b">
              <tr>
                <th className="table-th">Employee ID</th>
                <th className="table-th">Name</th>
                <th className="table-th">Username</th>
                <th className="table-th">Email</th>
                <th className="table-th">Status</th>
                <th className="table-th w-24">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {lecturers.map(lec => (
                <tr key={lec.id} className="hover:bg-gray-50">
                  <td className="table-td font-mono">{lec.employee_id}</td>
                  <td className="table-td font-medium">{lec.full_name}</td>
                  <td className="table-td">{lec.username}</td>
                  <td className="table-td">{lec.email}</td>
                  <td className="table-td"><span className={lec.is_active ? 'badge-green' : 'badge-red'}>{lec.is_active ? 'Active' : 'Inactive'}</span></td>
                  <td className="table-td">
                    {lec.is_active && (
                      <button className="btn-ghost p-1.5 text-red-500 hover:bg-red-50" onClick={() => setDeactivateId(lec.id)} title="Deactivate"><UserX size={15} /></button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {showCreate && (
        <Modal title="Add Lecturer" onClose={() => setShowCreate(false)} size="lg">
          <LecturerForm depts={depts} onSave={(d: any) => createMut.mutate(d)} onClose={() => setShowCreate(false)} />
        </Modal>
      )}

      {deactivateId && (
        <ConfirmDialog title="Deactivate Lecturer" message="Deactivate this lecturer?" onConfirm={() => deactivateMut.mutate(deactivateId)} onCancel={() => setDeactivateId(null)} danger />
      )}
    </div>
  )
}
