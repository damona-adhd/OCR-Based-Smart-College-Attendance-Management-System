import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Plus, Trash2 } from 'lucide-react'
import toast from 'react-hot-toast'
import { PageHeader } from '../../components/ui/PageHeader'
import { Modal } from '../../components/ui/Modal'
import { ConfirmDialog } from '../../components/ui/ConfirmDialog'
import { EmptyState } from '../../components/ui/EmptyState'
import { Spinner } from '../../components/ui/Spinner'
import { assignmentsApi } from '../../api/assignments'
import { lecturersApi } from '../../api/lecturers'
import { subjectsApi } from '../../api/subjects'
import { classesApi } from '../../api/classes'

function AssignmentForm({ lecturers, subjects, classes, onSave, onClose }: any) {
  const [lecturerId, setLecturerId] = useState('')
  const [subjectId, setSubjectId] = useState('')
  const [classId, setClassId] = useState('')
  return (
    <form onSubmit={e => { e.preventDefault(); onSave({ lecturer_id: Number(lecturerId), subject_id: Number(subjectId), class_id: Number(classId) }) }} className="space-y-4">
      <div>
        <label className="label">Lecturer</label>
        <select className="input" value={lecturerId} onChange={e => setLecturerId(e.target.value)} required>
          <option value="">Select lecturer</option>
          {lecturers.map((l: any) => <option key={l.id} value={l.id}>{l.full_name} ({l.employee_id})</option>)}
        </select>
      </div>
      <div>
        <label className="label">Subject</label>
        <select className="input" value={subjectId} onChange={e => setSubjectId(e.target.value)} required>
          <option value="">Select subject</option>
          {subjects.map((s: any) => <option key={s.id} value={s.id}>{s.subject_code} — {s.subject_name}</option>)}
        </select>
      </div>
      <div>
        <label className="label">Class</label>
        <select className="input" value={classId} onChange={e => setClassId(e.target.value)} required>
          <option value="">Select class</option>
          {classes.map((c: any) => <option key={c.id} value={c.id}>{c.name}</option>)}
        </select>
      </div>
      <div className="flex gap-3 justify-end pt-2">
        <button type="button" className="btn-secondary" onClick={onClose}>Cancel</button>
        <button type="submit" className="btn-primary">Assign</button>
      </div>
    </form>
  )
}

export default function AssignmentsPage() {
  const qc = useQueryClient()
  const [showCreate, setShowCreate] = useState(false)
  const [deleteId, setDeleteId] = useState<number | null>(null)

  const { data: assignments = [], isLoading } = useQuery({ queryKey: ['assignments'], queryFn: () => assignmentsApi.list() })
  const { data: lecturers = [] } = useQuery({ queryKey: ['lecturers'], queryFn: () => lecturersApi.list() })
  const { data: subjects = [] } = useQuery({ queryKey: ['subjects'], queryFn: () => subjectsApi.list() })
  const { data: classes = [] } = useQuery({ queryKey: ['classes'], queryFn: () => classesApi.list() })

  const createMut = useMutation({
    mutationFn: assignmentsApi.create,
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['assignments'] }); toast.success('Assignment created'); setShowCreate(false) },
    onError: (e: any) => toast.error(e.response?.data?.detail || 'Failed'),
  })
  const deleteMut = useMutation({
    mutationFn: assignmentsApi.delete,
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['assignments'] }); toast.success('Deleted'); setDeleteId(null) },
  })

  return (
    <div>
      <PageHeader title="Teaching Assignments" actions={
        <button className="btn-primary" onClick={() => setShowCreate(true)}><Plus size={16} />New Assignment</button>
      } />

      {isLoading ? <div className="flex justify-center py-16"><Spinner size="lg" /></div> :
       assignments.length === 0 ? <EmptyState title="No assignments yet" /> : (
        <div className="card p-0 overflow-hidden">
          <table className="w-full">
            <thead className="bg-gray-50 border-b">
              <tr>
                <th className="table-th">Lecturer</th>
                <th className="table-th">Subject</th>
                <th className="table-th">Class</th>
                <th className="table-th w-24">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {assignments.map(a => (
                <tr key={a.id} className="hover:bg-gray-50">
                  <td className="table-td">{a.lecturer?.full_name || a.lecturer_id}</td>
                  <td className="table-td">{a.subject?.subject_code} — {a.subject?.subject_name}</td>
                  <td className="table-td">{a.class_?.name || a.class_id}</td>
                  <td className="table-td">
                    <button className="btn-ghost p-1.5 text-red-500 hover:bg-red-50" onClick={() => setDeleteId(a.id)}><Trash2 size={15} /></button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {showCreate && (
        <Modal title="New Teaching Assignment" onClose={() => setShowCreate(false)}>
          <AssignmentForm lecturers={lecturers} subjects={subjects} classes={classes} onSave={(d: any) => createMut.mutate(d)} onClose={() => setShowCreate(false)} />
        </Modal>
      )}

      {deleteId && (
        <ConfirmDialog title="Remove Assignment" message="Remove this teaching assignment?" onConfirm={() => deleteMut.mutate(deleteId)} onCancel={() => setDeleteId(null)} danger />
      )}
    </div>
  )
}
