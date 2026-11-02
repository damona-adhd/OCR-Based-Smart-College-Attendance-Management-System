import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Plus, Pencil, Trash2 } from 'lucide-react'
import toast from 'react-hot-toast'
import { PageHeader } from '../../components/ui/PageHeader'
import { Modal } from '../../components/ui/Modal'
import { ConfirmDialog } from '../../components/ui/ConfirmDialog'
import { EmptyState } from '../../components/ui/EmptyState'
import { Spinner } from '../../components/ui/Spinner'
import { subjectsApi } from '../../api/subjects'
import { departmentsApi } from '../../api/departments'
import type { Subject } from '../../types'

function SubjectForm({ initial, depts, onSave, onClose }: any) {
  const [code, setCode] = useState(initial?.subject_code ?? '')
  const [name, setName] = useState(initial?.subject_name ?? '')
  const [semester, setSemester] = useState(initial?.semester ?? 1)
  const [deptId, setDeptId] = useState(initial?.department_id ?? '')
  return (
    <form onSubmit={e => { e.preventDefault(); onSave({ subject_code: code, subject_name: name, semester: Number(semester), department_id: Number(deptId) }) }} className="space-y-4">
      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className="label">Subject Code</label>
          <input className="input" value={code} onChange={e => setCode(e.target.value)} required placeholder="CS301" />
        </div>
        <div>
          <label className="label">Semester</label>
          <select className="input" value={semester} onChange={e => setSemester(e.target.value)}>
            {[1,2,3,4,5,6,7,8].map(s => <option key={s} value={s}>{s}</option>)}
          </select>
        </div>
      </div>
      <div>
        <label className="label">Subject Name</label>
        <input className="input" value={name} onChange={e => setName(e.target.value)} required placeholder="Data Structures" />
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

export default function SubjectsPage() {
  const qc = useQueryClient()
  const [modal, setModal] = useState<'create' | Subject | null>(null)
  const [deleteId, setDeleteId] = useState<number | null>(null)

  const { data: subjects = [], isLoading } = useQuery({ queryKey: ['subjects'], queryFn: () => subjectsApi.list() })
  const { data: depts = [] } = useQuery({ queryKey: ['departments'], queryFn: () => departmentsApi.list() })

  const createMut = useMutation({
    mutationFn: subjectsApi.create,
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['subjects'] }); toast.success('Subject created'); setModal(null) },
    onError: (e: any) => toast.error(e.response?.data?.detail || 'Failed'),
  })
  const updateMut = useMutation({
    mutationFn: ({ id, data }: any) => subjectsApi.update(id, data),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['subjects'] }); toast.success('Updated'); setModal(null) },
  })
  const deleteMut = useMutation({
    mutationFn: subjectsApi.delete,
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['subjects'] }); toast.success('Deleted'); setDeleteId(null) },
  })

  return (
    <div>
      <PageHeader title="Subjects" actions={
        <button className="btn-primary" onClick={() => setModal('create')}><Plus size={16} />Add Subject</button>
      } />

      {isLoading ? <div className="flex justify-center py-16"><Spinner size="lg" /></div> :
       subjects.length === 0 ? <EmptyState title="No subjects yet" /> : (
        <div className="card p-0 overflow-hidden">
          <table className="w-full">
            <thead className="bg-gray-50 border-b">
              <tr>
                <th className="table-th">Code</th>
                <th className="table-th">Name</th>
                <th className="table-th">Semester</th>
                <th className="table-th">Department</th>
                <th className="table-th w-24">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {subjects.map(sub => (
                <tr key={sub.id} className="hover:bg-gray-50">
                  <td className="table-td font-mono font-medium">{sub.subject_code}</td>
                  <td className="table-td">{sub.subject_name}</td>
                  <td className="table-td"><span className="badge-blue">Sem {sub.semester}</span></td>
                  <td className="table-td">{sub.department?.code || sub.department_id}</td>
                  <td className="table-td">
                    <div className="flex gap-2">
                      <button className="btn-ghost p-1.5" onClick={() => setModal(sub)}><Pencil size={15} /></button>
                      <button className="btn-ghost p-1.5 text-red-500 hover:bg-red-50" onClick={() => setDeleteId(sub.id)}><Trash2 size={15} /></button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {modal && (
        <Modal title={modal === 'create' ? 'Add Subject' : 'Edit Subject'} onClose={() => setModal(null)}>
          <SubjectForm
            initial={modal !== 'create' ? modal : undefined}
            depts={depts}
            onSave={(data: any) => modal === 'create' ? createMut.mutate(data) : updateMut.mutate({ id: (modal as Subject).id, data })}
            onClose={() => setModal(null)}
          />
        </Modal>
      )}

      {deleteId && (
        <ConfirmDialog title="Delete Subject" message="Delete this subject?" onConfirm={() => deleteMut.mutate(deleteId)} onCancel={() => setDeleteId(null)} danger />
      )}
    </div>
  )
}
