import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Plus, Pencil, UserX, UserCheck } from 'lucide-react'
import toast from 'react-hot-toast'
import { PageHeader } from '../../components/ui/PageHeader'
import { Modal } from '../../components/ui/Modal'
import { EmptyState } from '../../components/ui/EmptyState'
import { SearchInput } from '../../components/ui/SearchInput'
import { Spinner } from '../../components/ui/Spinner'
import { ConfirmDialog } from '../../components/ui/ConfirmDialog'
import { studentsApi } from '../../api/students'
import { departmentsApi } from '../../api/departments'
import { classesApi } from '../../api/classes'
import type { Student } from '../../types'

function StudentForm({ depts, classes, onSave, onClose }: any) {
  const [form, setForm] = useState({ usn: '', full_name: '', department_id: '', class_id: '', academic_year: '2024-25', semester: '3', username: '', email: '', password: '' })
  const set = (k: string) => (e: any) => setForm(f => ({ ...f, [k]: e.target.value }))
  return (
    <form onSubmit={e => { e.preventDefault(); onSave({ ...form, department_id: Number(form.department_id), class_id: Number(form.class_id), semester: Number(form.semester) }) }} className="space-y-4">
      <div className="grid grid-cols-2 gap-4">
        <div><label className="label">USN / Roll No.</label><input className="input" value={form.usn} onChange={set('usn')} required placeholder="1CS21CS001" /></div>
        <div><label className="label">Full Name</label><input className="input" value={form.full_name} onChange={set('full_name')} required /></div>
        <div><label className="label">Academic Year</label><input className="input" value={form.academic_year} onChange={set('academic_year')} required /></div>
        <div><label className="label">Semester</label><select className="input" value={form.semester} onChange={set('semester')}>{[1,2,3,4,5,6,7,8].map(s=><option key={s} value={s}>{s}</option>)}</select></div>
        <div><label className="label">Department</label><select className="input" value={form.department_id} onChange={set('department_id')} required><option value="">Select</option>{depts.map((d:any)=><option key={d.id} value={d.id}>{d.name}</option>)}</select></div>
        <div><label className="label">Class</label><select className="input" value={form.class_id} onChange={set('class_id')} required><option value="">Select</option>{classes.map((c:any)=><option key={c.id} value={c.id}>{c.name}</option>)}</select></div>
      </div>
      <p className="text-xs text-gray-500 pt-2 border-t">Optional: Create a login account for this student</p>
      <div className="grid grid-cols-2 gap-4">
        <div><label className="label">Username</label><input className="input" value={form.username} onChange={set('username')} placeholder="Optional" /></div>
        <div><label className="label">Email</label><input className="input" type="email" value={form.email} onChange={set('email')} placeholder="Optional" /></div>
        <div><label className="label">Password</label><input className="input" type="password" value={form.password} onChange={set('password')} placeholder="Optional" /></div>
      </div>
      <div className="flex gap-3 justify-end pt-2">
        <button type="button" className="btn-secondary" onClick={onClose}>Cancel</button>
        <button type="submit" className="btn-primary">Create Student</button>
      </div>
    </form>
  )
}

export default function StudentsPage() {
  const qc = useQueryClient()
  const [search, setSearch] = useState('')
  const [showCreate, setShowCreate] = useState(false)
  const [deactivateId, setDeactivateId] = useState<number | null>(null)

  const { data: students = [], isLoading } = useQuery({ queryKey: ['students', { is_active: true }], queryFn: () => studentsApi.list({ is_active: true, limit: 200 }) })
  const { data: depts = [] } = useQuery({ queryKey: ['departments'], queryFn: () => departmentsApi.list() })
  const { data: classes = [] } = useQuery({ queryKey: ['classes'], queryFn: () => classesApi.list() })

  const createMut = useMutation({
    mutationFn: studentsApi.create,
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['students'] }); toast.success('Student created'); setShowCreate(false) },
    onError: (e: any) => toast.error(e.response?.data?.detail || 'Failed'),
  })
  const deactivateMut = useMutation({
    mutationFn: studentsApi.deactivate,
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['students'] }); toast.success('Student deactivated'); setDeactivateId(null) },
  })

  const filtered = students.filter(s =>
    s.full_name.toLowerCase().includes(search.toLowerCase()) ||
    s.usn.toLowerCase().includes(search.toLowerCase())
  )

  return (
    <div>
      <PageHeader title="Students" subtitle={`${students.length} active students`} actions={
        <>
          <SearchInput value={search} onChange={setSearch} placeholder="Search by name or USN" />
          <button className="btn-primary" onClick={() => setShowCreate(true)}><Plus size={16} />Add Student</button>
        </>
      } />

      {isLoading ? <div className="flex justify-center py-16"><Spinner size="lg" /></div> :
       filtered.length === 0 ? <EmptyState title="No students found" /> : (
        <div className="card p-0 overflow-hidden">
          <table className="w-full">
            <thead className="bg-gray-50 border-b">
              <tr>
                <th className="table-th">USN</th>
                <th className="table-th">Name</th>
                <th className="table-th">Class</th>
                <th className="table-th">Year</th>
                <th className="table-th">Status</th>
                <th className="table-th w-24">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {filtered.map(s => (
                <tr key={s.id} className="hover:bg-gray-50">
                  <td className="table-td font-mono text-xs">{s.usn}</td>
                  <td className="table-td font-medium">{s.full_name}</td>
                  <td className="table-td">{classes.find(c => c.id === s.class_id)?.name || s.class_id}</td>
                  <td className="table-td">{s.academic_year}</td>
                  <td className="table-td"><span className={s.is_active ? 'badge-green' : 'badge-red'}>{s.is_active ? 'Active' : 'Inactive'}</span></td>
                  <td className="table-td">
                    {s.is_active && (
                      <button className="btn-ghost p-1.5 text-red-500 hover:bg-red-50" onClick={() => setDeactivateId(s.id)} title="Deactivate"><UserX size={15} /></button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {showCreate && (
        <Modal title="Add Student" onClose={() => setShowCreate(false)} size="lg">
          <StudentForm depts={depts} classes={classes} onSave={(d: any) => createMut.mutate(d)} onClose={() => setShowCreate(false)} />
        </Modal>
      )}

      {deactivateId && (
        <ConfirmDialog title="Deactivate Student" message="Deactivate this student? They will no longer appear in active rosters." onConfirm={() => deactivateMut.mutate(deactivateId)} onCancel={() => setDeactivateId(null)} danger />
      )}
    </div>
  )
}
