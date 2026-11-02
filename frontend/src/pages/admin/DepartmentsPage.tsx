import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Plus, Pencil, Trash2 } from 'lucide-react'
import toast from 'react-hot-toast'
import { PageHeader } from '../../components/ui/PageHeader'
import { Modal } from '../../components/ui/Modal'
import { ConfirmDialog } from '../../components/ui/ConfirmDialog'
import { EmptyState } from '../../components/ui/EmptyState'
import { SearchInput } from '../../components/ui/SearchInput'
import { Spinner } from '../../components/ui/Spinner'
import { departmentsApi } from '../../api/departments'
import type { Department } from '../../types'

function DeptForm({ initial, onSave, onClose }: {
  initial?: Department; onSave: (d: { name: string; code: string }) => void; onClose: () => void
}) {
  const [name, setName] = useState(initial?.name ?? '')
  const [code, setCode] = useState(initial?.code ?? '')
  return (
    <form onSubmit={e => { e.preventDefault(); onSave({ name, code }) }} className="space-y-4">
      <div>
        <label className="label">Department Name</label>
        <input className="input" value={name} onChange={e => setName(e.target.value)} required placeholder="e.g. Computer Science" />
      </div>
      <div>
        <label className="label">Department Code</label>
        <input className="input uppercase" value={code} onChange={e => setCode(e.target.value.toUpperCase())} required placeholder="e.g. CSE" maxLength={10} />
      </div>
      <div className="flex gap-3 justify-end pt-2">
        <button type="button" className="btn-secondary" onClick={onClose}>Cancel</button>
        <button type="submit" className="btn-primary">{initial ? 'Update' : 'Create'}</button>
      </div>
    </form>
  )
}

export default function DepartmentsPage() {
  const qc = useQueryClient()
  const [search, setSearch] = useState('')
  const [modal, setModal] = useState<'create' | Department | null>(null)
  const [deleteId, setDeleteId] = useState<number | null>(null)

  const { data: departments = [], isLoading } = useQuery({
    queryKey: ['departments'], queryFn: departmentsApi.list
  })

  const createMut = useMutation({
    mutationFn: departmentsApi.create,
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['departments'] }); toast.success('Department created'); setModal(null) },
    onError: (e: any) => toast.error(e.response?.data?.detail || 'Failed'),
  })

  const updateMut = useMutation({
    mutationFn: ({ id, data }: { id: number; data: Partial<Department> }) => departmentsApi.update(id, data),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['departments'] }); toast.success('Department updated'); setModal(null) },
    onError: (e: any) => toast.error(e.response?.data?.detail || 'Failed'),
  })

  const deleteMut = useMutation({
    mutationFn: departmentsApi.delete,
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['departments'] }); toast.success('Department deleted'); setDeleteId(null) },
    onError: (e: any) => toast.error(e.response?.data?.detail || 'Failed'),
  })

  const filtered = departments.filter(d =>
    d.name.toLowerCase().includes(search.toLowerCase()) ||
    d.code.toLowerCase().includes(search.toLowerCase())
  )

  return (
    <div>
      <PageHeader
        title="Departments"
        actions={
          <>
            <SearchInput value={search} onChange={setSearch} placeholder="Search departments" />
            <button className="btn-primary" onClick={() => setModal('create')}><Plus size={16} />Add Department</button>
          </>
        }
      />

      {isLoading ? (
        <div className="flex justify-center py-16"><Spinner size="lg" /></div>
      ) : filtered.length === 0 ? (
        <EmptyState title="No departments found" description="Add your first department to get started" action={<button className="btn-primary" onClick={() => setModal('create')}><Plus size={16}/>Add Department</button>} />
      ) : (
        <div className="card p-0 overflow-hidden">
          <table className="w-full">
            <thead className="bg-gray-50 border-b">
              <tr>
                <th className="table-th">Name</th>
                <th className="table-th">Code</th>
                <th className="table-th w-24">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {filtered.map(dept => (
                <tr key={dept.id} className="hover:bg-gray-50">
                  <td className="table-td font-medium">{dept.name}</td>
                  <td className="table-td"><span className="badge-blue">{dept.code}</span></td>
                  <td className="table-td">
                    <div className="flex gap-2">
                      <button className="btn-ghost p-1.5" onClick={() => setModal(dept)} title="Edit"><Pencil size={15} /></button>
                      <button className="btn-ghost p-1.5 text-red-500 hover:bg-red-50" onClick={() => setDeleteId(dept.id)} title="Delete"><Trash2 size={15} /></button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {modal && (
        <Modal title={modal === 'create' ? 'Add Department' : 'Edit Department'} onClose={() => setModal(null)}>
          <DeptForm
            initial={modal !== 'create' ? modal : undefined}
            onSave={data => modal === 'create' ? createMut.mutate(data) : updateMut.mutate({ id: (modal as Department).id, data })}
            onClose={() => setModal(null)}
          />
        </Modal>
      )}

      {deleteId && (
        <ConfirmDialog
          title="Delete Department"
          message="This will delete the department. This action cannot be undone."
          onConfirm={() => deleteMut.mutate(deleteId)}
          onCancel={() => setDeleteId(null)}
          danger
        />
      )}
    </div>
  )
}
