import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Plus, Pencil, Trash2 } from 'lucide-react'
import toast from 'react-hot-toast'
import { PageHeader } from '../../components/ui/PageHeader'
import { Modal } from '../../components/ui/Modal'
import { ConfirmDialog } from '../../components/ui/ConfirmDialog'
import { EmptyState } from '../../components/ui/EmptyState'
import { Spinner } from '../../components/ui/Spinner'
import { classesApi } from '../../api/classes'
import { departmentsApi } from '../../api/departments'
import type { Class } from '../../types'

function ClassForm({ initial, depts, onSave, onClose }: any) {
  const [name, setName] = useState(initial?.name ?? '')
  const [academicYear, setAcademicYear] = useState(initial?.academic_year ?? '2024-25')
  const [semester, setSemester] = useState(initial?.semester ?? 1)
  const [deptId, setDeptId] = useState(initial?.department_id ?? '')

  return (
    <form onSubmit={e => { e.preventDefault(); onSave({ name, academic_year: academicYear, semester: Number(semester), department_id: Number(deptId) }) }} className="space-y-4">
      <div>
        <label className="label">Class Name</label>
        <input className="input" value={name} onChange={e => setName(e.target.value)} required placeholder="e.g. CSE 3A" />
      </div>
      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className="label">Academic Year</label>
          <input className="input" value={academicYear} onChange={e => setAcademicYear(e.target.value)} required placeholder="2024-25" />
        </div>
        <div>
          <label className="label">Semester</label>
          <select className="input" value={semester} onChange={e => setSemester(e.target.value)}>
            {[1,2,3,4,5,6,7,8].map(s => <option key={s} value={s}>{s}</option>)}
          </select>
        </div>
      </div>
      <div>
        <label className="label">Department</label>
        <select className="input" value={deptId} onChange={e => setDeptId(e.target.value)} required>
          <option value="">Select department</option>
          {depts.map((d: any) => <option key={d.id} value={d.id}>{d.name} ({d.code})</option>)}
        </select>
      </div>
      <div className="flex gap-3 justify-end pt-2">
        <button type="button" className="btn-secondary" onClick={onClose}>Cancel</button>
        <button type="submit" className="btn-primary">{initial ? 'Update' : 'Create'}</button>
      </div>
    </form>
  )
}

export default function ClassesPage() {
  const qc = useQueryClient()
  const [modal, setModal] = useState<'create' | Class | null>(null)
  const [deleteId, setDeleteId] = useState<number | null>(null)

  const { data: classes = [], isLoading } = useQuery({ queryKey: ['classes'], queryFn: () => classesApi.list() })
  const { data: depts = [] } = useQuery({ queryKey: ['departments'], queryFn: () => departmentsApi.list() })

  const createMut = useMutation({
    mutationFn: classesApi.create,
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['classes'] }); toast.success('Class created'); setModal(null) },
    onError: (e: any) => toast.error(e.response?.data?.detail || 'Failed'),
  })
  const updateMut = useMutation({
    mutationFn: ({ id, data }: any) => classesApi.update(id, data),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['classes'] }); toast.success('Updated'); setModal(null) },
  })
  const deleteMut = useMutation({
    mutationFn: classesApi.delete,
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['classes'] }); toast.success('Deleted'); setDeleteId(null) },
  })

  return (
    <div>
      <PageHeader title="Classes" actions={
        <button className="btn-primary" onClick={() => setModal('create')}><Plus size={16} />Add Class</button>
      } />

      {isLoading ? <div className="flex justify-center py-16"><Spinner size="lg" /></div> :
       classes.length === 0 ? <EmptyState title="No classes yet" /> : (
        <div className="card p-0 overflow-hidden">
          <table className="w-full">
            <thead className="bg-gray-50 border-b">
              <tr>
                <th className="table-th">Name</th>
                <th className="table-th">Academic Year</th>
                <th className="table-th">Semester</th>
                <th className="table-th">Department</th>
                <th className="table-th w-24">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {classes.map(cls => (
                <tr key={cls.id} className="hover:bg-gray-50">
                  <td className="table-td font-medium">{cls.name}</td>
                  <td className="table-td">{cls.academic_year}</td>
                  <td className="table-td"><span className="badge-blue">Sem {cls.semester}</span></td>
                  <td className="table-td">{cls.department?.code || cls.department_id}</td>
                  <td className="table-td">
                    <div className="flex gap-2">
                      <button className="btn-ghost p-1.5" onClick={() => setModal(cls)}><Pencil size={15} /></button>
                      <button className="btn-ghost p-1.5 text-red-500 hover:bg-red-50" onClick={() => setDeleteId(cls.id)}><Trash2 size={15} /></button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {modal && (
        <Modal title={modal === 'create' ? 'Add Class' : 'Edit Class'} onClose={() => setModal(null)}>
          <ClassForm
            initial={modal !== 'create' ? modal : undefined}
            depts={depts}
            onSave={(data: any) => modal === 'create' ? createMut.mutate(data) : updateMut.mutate({ id: (modal as Class).id, data })}
            onClose={() => setModal(null)}
          />
        </Modal>
      )}

      {deleteId && (
        <ConfirmDialog title="Delete Class" message="Delete this class?" onConfirm={() => deleteMut.mutate(deleteId)} onCancel={() => setDeleteId(null)} danger />
      )}
    </div>
  )
}
