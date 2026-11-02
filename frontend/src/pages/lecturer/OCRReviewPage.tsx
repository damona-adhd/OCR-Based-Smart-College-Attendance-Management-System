import { useState, useEffect } from 'react'
import { useParams, useLocation, useNavigate, Link } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import toast from 'react-hot-toast'
import {
  AlertTriangle,
  CheckCircle,
  HelpCircle,
  XCircle,
  RefreshCw,
  UserPlus,
  ArrowLeft,
  FileText,
  Sliders,
  Check,
  X,
  Sparkles,
  Info,
  Trash2,
} from 'lucide-react'
import { PageHeader } from '../../components/ui/PageHeader'
import { Spinner } from '../../components/ui/Spinner'
import { ConfirmDialog } from '../../components/ui/ConfirmDialog'
import { ocrApi } from '../../api/ocr'
import { studentsApi } from '../../api/students'
import { attendanceApi } from '../../api/attendance'
import type { OCRRow, OCRResult, MatchStatus } from '../../types'

const matchBadgeConfig: Record<MatchStatus, { badge: string; icon: React.ReactNode; label: string }> = {
  matched:   { badge: 'badge-green',  icon: <CheckCircle size={14} className="text-green-600" />,  label: 'Matched' },
  uncertain: { badge: 'badge-yellow', icon: <HelpCircle size={14} className="text-yellow-600" />, label: 'Uncertain' },
  ambiguous: { badge: 'badge-yellow', icon: <AlertTriangle size={14} className="text-amber-600" />, label: 'Ambiguous' },
  unmatched: { badge: 'badge-red',    icon: <XCircle size={14} className="text-red-600" />,       label: 'Unmatched' },
  duplicate: { badge: 'badge-red',    icon: <AlertTriangle size={14} className="text-red-600" />,  label: 'Duplicate' },
  missing:   { badge: 'badge-gray',   icon: <AlertTriangle size={14} className="text-gray-400" />, label: 'Missing' },
}

export default function OCRReviewPage() {
  const { sessionId } = useParams<{ sessionId: string }>()
  const location = useLocation()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const id = Number(sessionId)

  const [rows, setRows] = useState<OCRRow[]>([])
  const [selectedProvider, setSelectedProvider] = useState<string>('auto')
  const [showConfirm, setShowConfirm] = useState(false)
  const [showAddStudent, setShowAddStudent] = useState(false)
  const [newStudentName, setNewStudentName] = useState('')
  const [newStudentUsn, setNewStudentUsn] = useState('')
  const [addingStudent, setAddingStudent] = useState(false)
  const [activeRowForStudent, setActiveRowForStudent] = useState<number | null>(null)

  const { data: session } = useQuery({
    queryKey: ['session', id],
    queryFn: () => attendanceApi.getSession(id),
  })

  const { data: students = [], refetch: refetchStudents } = useQuery({
    queryKey: ['class-roster', session?.class_id],
    queryFn: () => studentsApi.classRoster(session!.class_id),
    enabled: !!session?.class_id,
  })

  // Load initial OCR result from navigation state
  const [result, setResult] = useState<OCRResult | undefined>((location.state as any)?.result)

  const mapResultToRows = (res: OCRResult): OCRRow[] => {
    return res.rows.map(r => ({
      ...r,
      corrected_student_id: r.matched_student_id || undefined,
      corrected_status: r.attendance_status === 'present' ? 'present' : (r.attendance_status === 'absent' ? 'absent' : (r.proposed_status || 'unknown')),
    }))
  }

  useEffect(() => {
    if (result && result.rows) {
      setRows(mapResultToRows(result))
    }
  }, [result?.session_id])

  // Reprocess mutation with provider selection
  const reprocessMut = useMutation({
    mutationFn: (provider: string) => ocrApi.processOCR(id, provider),
    onSuccess: (res) => {
      toast.success(`Document reprocessed using ${res.extraction_provider || selectedProvider}`)
      setResult(res)
      setRows(mapResultToRows(res))
    },
    onError: (e: any) => {
      toast.error(e.response?.data?.detail || 'Document processing failed')
    },
  })

  // Finalize attendance mutation
  const confirmMut = useMutation({
    mutationFn: () =>
      ocrApi.confirmOCR(
        id,
        rows.map(r => ({
          row_index: r.row_index,
          student_id: r.corrected_student_id || 0,
          attendance_status: r.corrected_status === 'present' ? 'present' : 'absent',
        }))
      ),
    onSuccess: () => {
      toast.success('Attendance confirmed and finalized successfully!')
      navigate(`/lecturer/sessions/${id}`)
    },
    onError: (e: any) => toast.error(e.response?.data?.detail || 'Finalization failed'),
  })

  const handleQuickAddStudent = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!session?.class_id || !newStudentName.trim() || !newStudentUsn.trim()) return

    setAddingStudent(true)
    try {
      const added = await studentsApi.quickAdd({
        full_name: newStudentName.trim(),
        usn: newStudentUsn.trim().toUpperCase(),
        class_id: session.class_id,
      })
      toast.success(`Enrolled ${added.full_name} (${added.usn})`)
      await queryClient.invalidateQueries({ queryKey: ['class-roster', session.class_id] })

      // Auto-assign to row if triggered from a specific row
      if (activeRowForStudent !== null) {
        setRows(prev =>
          prev.map(r =>
            r.row_index === activeRowForStudent
              ? {
                  ...r,
                  corrected_student_id: added.id,
                  matched_student_name: added.full_name,
                  matched_student_usn: added.usn,
                  match_status: 'matched',
                  needs_review: r.corrected_status === 'unknown',
                }
              : r
          )
        )
      }

      setShowAddStudent(false)
      setNewStudentName('')
      setNewStudentUsn('')
      setActiveRowForStudent(null)
    } catch (err: any) {
      toast.error(err.response?.data?.detail || 'Failed to add student')
    } finally {
      setAddingStudent(false)
    }
  }

  const openQuickAddForRow = (rowIndex: number, name?: string, usn?: string) => {
    setActiveRowForStudent(rowIndex)
    setNewStudentName(name || '')
    setNewStudentUsn(usn || '')
    setShowAddStudent(true)
  }

  const setRowStatus = (rowIndex: number, status: string) =>
    setRows(prev =>
      prev.map(r =>
        r.row_index === rowIndex
          ? {
              ...r,
              corrected_status: status,
              needs_review: !r.corrected_student_id,
            }
          : r
      )
    )

  const setRowStudent = (rowIndex: number, studentId: number) => {
    const found = students.find(s => s.id === studentId)
    setRows(prev =>
      prev.map(r =>
        r.row_index === rowIndex
          ? {
              ...r,
              corrected_student_id: studentId,
              matched_student_name: found?.full_name,
              matched_student_usn: found?.usn,
              match_status: studentId ? 'matched' : 'unmatched',
              needs_review: !studentId || r.corrected_status === 'unknown',
            }
          : r
      )
    )
  }

  const markAllStatus = (status: 'present' | 'absent') => {
    setRows(prev =>
      prev.map(r => ({
        ...r,
        corrected_status: status,
        needs_review: !r.corrected_student_id,
      }))
    )
    toast.success(`Marked all records as ${status}`)
  }

  const removeRow = (rowIndex: number) => {
    setRows(prev => prev.filter(r => r.row_index !== rowIndex))
    toast.success('Row removed')
  }

  // Finalization Validation Logic
  const totalRows = rows.length
  const unassignedCount = rows.filter(r => !r.corrected_student_id).length
  const unknownCount = rows.filter(r => r.corrected_status === 'unknown').length
  const presentCount = rows.filter(r => r.corrected_status === 'present').length
  const absentCount = rows.filter(r => r.corrected_status === 'absent').length

  // Duplicate student detection
  const studentCountMap = new Map<number, number>()
  rows.forEach(r => {
    if (r.corrected_student_id) {
      studentCountMap.set(r.corrected_student_id, (studentCountMap.get(r.corrected_student_id) || 0) + 1)
    }
  })
  const duplicateStudentIds = new Set<number>(
    Array.from(studentCountMap.entries())
      .filter(([_, count]) => count > 1)
      .map(([sid]) => sid)
  )
  const duplicateCount = duplicateStudentIds.size

  const canFinalize =
    totalRows > 0 &&
    unassignedCount === 0 &&
    unknownCount === 0 &&
    duplicateCount === 0 &&
    !confirmMut.isPending

  let finalizeDisabledReason = ''
  if (totalRows === 0) {
    finalizeDisabledReason = '0 records found. Run extraction or enter attendance manually.'
  } else if (unassignedCount > 0) {
    finalizeDisabledReason = `${unassignedCount} candidate row(s) require an assigned student before finalization.`
  } else if (unknownCount > 0) {
    finalizeDisabledReason = `${unknownCount} row(s) have unknown attendance marks. Set them to Present or Absent.`
  } else if (duplicateCount > 0) {
    const dupNames = Array.from(duplicateStudentIds)
      .map(sid => {
        const found = students.find(s => s.id === sid)
        return found ? `${found.full_name} (${found.usn})` : `ID ${sid}`
      })
      .join(', ')
    finalizeDisabledReason = `Duplicate student detected: ${dupNames}. Each student can only be marked once per session. Remove or reassign extra rows.`
  }

  if (!result && rows.length === 0) {
    return (
      <div className="card text-center py-12 max-w-lg mx-auto my-12">
        <div className="w-16 h-16 rounded-2xl bg-forest-50 text-forest mx-auto flex items-center justify-center mb-4">
          <FileText size={32} />
        </div>
        <h3 className="text-lg font-bold text-ink-primary mb-2">No Document Extraction Results Yet</h3>
        <p className="text-sm text-ink-secondary mb-6">
          Process the uploaded register document to extract student attendance records.
        </p>
        <div className="flex flex-col sm:flex-row gap-3 justify-center">
          <button
            className="btn-primary flex items-center justify-center gap-2"
            onClick={() => reprocessMut.mutate(selectedProvider)}
            disabled={reprocessMut.isPending}
          >
            {reprocessMut.isPending ? <Spinner size="sm" /> : <RefreshCw size={16} />}
            <span>Run Extraction Now</span>
          </button>
          <Link to={`/lecturer/sessions/${id}/manual`} className="btn-secondary">
            Switch to Manual Attendance
          </Link>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Top Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <Link
            to={`/lecturer/sessions/${id}`}
            className="inline-flex items-center gap-1.5 text-xs text-ink-secondary hover:text-ink-primary mb-1 transition-colors"
          >
            <ArrowLeft size={14} /> Back to Session
          </Link>
          <h1 className="text-2xl font-bold text-ink-primary tracking-tight">Review Extracted Attendance</h1>
          <p className="text-xs text-ink-secondary mt-0.5">
            {session ? `Session #${id} • ${session.subject_name || 'Subject'} (${session.class_name || 'Class'}) • ${session.attendance_date}` : ''}
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2.5">
          {/* Provider selector & re-run */}
          <div className="flex items-center gap-1.5 bg-white border border-ink-border rounded-lg px-2.5 py-1.5 shadow-sm text-xs">
            <Sliders size={14} className="text-ink-secondary" />
            <span className="text-ink-secondary font-medium">Engine:</span>
            <select
              value={selectedProvider}
              onChange={e => setSelectedProvider(e.target.value)}
              className="bg-transparent font-semibold text-ink-primary focus:outline-none"
            >
              <option value="auto">Auto (Smart Routing)</option>
              <option value="gemini">Gemini Vision (Handwritten)</option>
              <option value="pymupdf">PyMuPDF (Direct Table)</option>
              <option value="tesseract">Tesseract (OCR Fallback)</option>
            </select>
            <button
              onClick={() => reprocessMut.mutate(selectedProvider)}
              disabled={reprocessMut.isPending}
              className="ml-1 text-forest hover:text-forest-dark font-medium flex items-center gap-1"
              title="Re-run extraction with chosen engine"
            >
              <RefreshCw size={13} className={reprocessMut.isPending ? 'animate-spin' : ''} />
              Re-run
            </button>
          </div>

          <button
            onClick={() => {
              setActiveRowForStudent(null)
              setNewStudentName('')
              setNewStudentUsn('')
              setShowAddStudent(true)
            }}
            className="btn-secondary text-xs flex items-center gap-1.5"
          >
            <UserPlus size={14} />
            <span>Add Student to Class</span>
          </button>

          <Link to={`/lecturer/sessions/${id}/manual`} className="btn-secondary text-xs">
            Manual Entry
          </Link>
        </div>
      </div>

      {/* Provider Info & Diagnostic Notice */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="card p-4">
          <p className="text-xs text-ink-secondary">Extraction Engine</p>
          <div className="flex items-center gap-2 mt-1">
            <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-forest-100 text-forest capitalize">
              <Sparkles size={12} />
              {result?.extraction_provider || 'auto'}
            </span>
            <span className="text-xs text-ink-secondary">{result?.page_count || 1} page(s)</span>
          </div>
        </div>

        <div className="card p-4">
          <p className="text-xs text-ink-secondary">Candidate Rows Extracted</p>
          <p className="text-xl font-bold text-ink-primary mt-1">{result?.total_candidate_rows ?? rows.length}</p>
        </div>

        <div className="card p-4">
          <p className="text-xs text-ink-secondary">Enrolled Roster Matches</p>
          <div className="flex items-baseline gap-2 mt-1">
            <p className="text-xl font-bold text-green-700">{rows.filter(r => r.match_status === 'matched').length}</p>
            <span className="text-xs text-ink-secondary">of {students.length} students</span>
          </div>
        </div>

        <div className="card p-4">
          <p className="text-xs text-ink-secondary">Attendance Breakdown</p>
          <div className="flex items-center gap-2 mt-1 text-xs font-semibold">
            <span className="text-green-700 bg-green-50 px-2 py-0.5 rounded">{presentCount} Present</span>
            <span className="text-red-700 bg-red-50 px-2 py-0.5 rounded">{absentCount} Absent</span>
            {unknownCount > 0 && (
              <span className="text-amber-800 bg-amber-50 px-2 py-0.5 rounded">{unknownCount} Unknown</span>
            )}
          </div>
        </div>
      </div>

      {/* Diagnostic Note / Alerts */}
      {result?.processing_note && (
        <div className="bg-amber-50 border border-amber-200 rounded-xl p-4 text-xs text-amber-900 flex items-start gap-2.5">
          <Info size={16} className="text-amber-700 shrink-0 mt-0.5" />
          <div className="flex-1">
            <p className="font-semibold mb-0.5">Document Processing Diagnostics</p>
            <p>{result.processing_note}</p>
          </div>
        </div>
      )}

      {/* Bulk actions & Quick filters */}
      <div className="flex flex-wrap items-center justify-between gap-3 bg-white p-3 rounded-xl border border-ink-border text-xs">
        <div className="flex items-center gap-2">
          <span className="font-medium text-ink-secondary">Quick Set All:</span>
          <button
            onClick={() => markAllStatus('present')}
            className="px-2.5 py-1 rounded bg-green-50 hover:bg-green-100 text-green-800 font-semibold transition-colors"
          >
            Mark All Present
          </button>
          <button
            onClick={() => markAllStatus('absent')}
            className="px-2.5 py-1 rounded bg-red-50 hover:bg-red-100 text-red-800 font-semibold transition-colors"
          >
            Mark All Absent
          </button>
        </div>

        <div className="flex items-center gap-2 text-ink-secondary">
          <span>Roster: {students.length} enrolled</span>
          <span>•</span>
          <span className={unassignedCount > 0 ? 'text-red-600 font-bold' : 'text-green-600'}>
            {unassignedCount} unassigned
          </span>
          <span>•</span>
          <span className={unknownCount > 0 ? 'text-amber-600 font-bold' : 'text-gray-500'}>
            {unknownCount} unresolved marks
          </span>
          {duplicateCount > 0 && (
            <>
              <span>•</span>
              <span className="text-red-600 font-bold flex items-center gap-1">
                <AlertTriangle size={12} />
                {duplicateCount} duplicate student(s)
              </span>
            </>
          )}
        </div>
      </div>

      {/* Main Review Table */}
      <div className="card p-0 overflow-hidden shadow-sm">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-gray-50/80 border-b border-ink-border text-ink-secondary uppercase tracking-wider font-semibold">
              <tr>
                <th className="py-3 px-3 w-12 text-center">Row</th>
                <th className="py-3 px-3 w-12 text-center">Page</th>
                <th className="py-3 px-3">Extracted USN</th>
                <th className="py-3 px-3">Extracted Name</th>
                <th className="py-3 px-2 text-center w-16">Mark</th>
                <th className="py-3 px-3">Match Status</th>
                <th className="py-3 px-3 min-w-[200px]">Enrolled Student</th>
                <th className="py-3 px-3 w-28 text-center">Final Attendance</th>
                <th className="py-3 px-3">Review Notes</th>
                <th className="py-3 px-2 text-center w-12">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {rows.map(row => {
                const badge = matchBadgeConfig[row.match_status] || matchBadgeConfig.unmatched
                const isUnassigned = !row.corrected_student_id
                const isUnknownStatus = row.corrected_status === 'unknown'
                const isDuplicate = !!row.corrected_student_id && duplicateStudentIds.has(row.corrected_student_id)

                return (
                  <tr
                    key={row.row_index}
                    className={`hover:bg-gray-50/80 transition-colors ${
                      isDuplicate
                        ? 'bg-red-50/60 border-l-4 border-l-red-500'
                        : isUnassigned || isUnknownStatus
                        ? 'bg-amber-50/20'
                        : ''
                    }`}
                  >
                    <td className="py-2.5 px-3 text-center font-mono text-gray-400">{row.row_index}</td>
                    <td className="py-2.5 px-3 text-center text-gray-400">{row.page_number || 1}</td>
                    <td className="py-2.5 px-3 font-mono font-medium text-ink-primary">
                      {row.extracted_usn || row.usn || <span className="text-gray-300">—</span>}
                    </td>
                    <td className="py-2.5 px-3 font-medium text-ink-primary">
                      {row.extracted_name || row.student_name || <span className="text-gray-300">—</span>}
                    </td>
                    <td className="py-2.5 px-2 text-center">
                      <span className="inline-block px-1.5 py-0.5 rounded font-mono font-bold bg-gray-100 text-gray-700">
                        {row.raw_attendance_mark || '—'}
                      </span>
                    </td>
                    <td className="py-2.5 px-3">
                      <div className="flex items-center gap-1.5">
                        {badge.icon}
                        <span className={`text-[11px] font-semibold px-2 py-0.5 rounded-full ${badge.badge}`}>
                          {badge.label}
                        </span>
                      </div>
                    </td>
                    <td className="py-2.5 px-3">
                      <div className="flex items-center gap-1.5">
                        <select
                          className={`input py-1 text-xs w-full ${
                            isDuplicate
                              ? 'border-red-500 bg-red-50/60 font-semibold text-red-900'
                              : isUnassigned
                              ? 'border-red-400 bg-red-50/30'
                              : ''
                          }`}
                          value={row.corrected_student_id || ''}
                          onChange={e => setRowStudent(row.row_index, Number(e.target.value))}
                        >
                          <option value="">-- Assign Enrolled Student --</option>
                          {students.map(s => {
                            const isAlreadyAssigned =
                              s.id !== row.corrected_student_id &&
                              rows.some(other => other.corrected_student_id === s.id)
                            return (
                              <option key={s.id} value={s.id}>
                                {s.usn} — {s.full_name} {isAlreadyAssigned ? '(Assigned)' : ''}
                              </option>
                            )
                          })}
                        </select>
                        {isUnassigned && (
                          <button
                            onClick={() => openQuickAddForRow(row.row_index, row.extracted_name || row.student_name, row.extracted_usn || row.usn)}
                            title="Quick enroll this student to class"
                            className="p-1 rounded bg-forest-50 hover:bg-forest-100 text-forest shrink-0 transition-colors"
                          >
                            <UserPlus size={14} />
                          </button>
                        )}
                      </div>
                    </td>
                    <td className="py-2.5 px-3 text-center">
                      <div className="inline-flex rounded-lg border border-ink-border overflow-hidden shadow-xs">
                        <button
                          type="button"
                          className={`px-3 py-1 font-bold text-xs transition-colors ${
                            row.corrected_status === 'present'
                              ? 'bg-green-600 text-white'
                              : 'bg-white text-gray-600 hover:bg-green-50'
                          }`}
                          onClick={() => setRowStatus(row.row_index, 'present')}
                        >
                          P
                        </button>
                        <button
                          type="button"
                          className={`px-3 py-1 font-bold text-xs border-l border-ink-border transition-colors ${
                            row.corrected_status === 'absent'
                              ? 'bg-red-600 text-white'
                              : 'bg-white text-gray-600 hover:bg-red-50'
                          }`}
                          onClick={() => setRowStatus(row.row_index, 'absent')}
                        >
                          A
                        </button>
                      </div>
                      {isUnknownStatus && (
                        <p className="text-[10px] text-amber-600 font-semibold mt-0.5">Select P/A</p>
                      )}
                    </td>
                    <td className="py-2.5 px-3 text-ink-secondary text-[11px] max-w-xs">
                      {isDuplicate ? (
                        <span className="text-red-600 font-semibold flex items-center gap-1">
                          <AlertTriangle size={12} className="shrink-0" /> Duplicate student assigned
                        </span>
                      ) : (
                        row.review_reason || (isUnassigned ? 'Select student to confirm' : 'Verified')
                      )}
                    </td>
                    <td className="py-2.5 px-2 text-center">
                      <button
                        type="button"
                        onClick={() => removeRow(row.row_index)}
                        title="Remove row"
                        className="p-1.5 rounded-lg text-gray-400 hover:text-red-600 hover:bg-red-50 transition-colors"
                      >
                        <Trash2 size={14} />
                      </button>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      </div>

      {/* Confirmation & Finalization Bottom Bar */}
      <div className="bg-white border border-ink-border rounded-2xl p-5 shadow-sm flex flex-col sm:flex-row items-center justify-between gap-4">
        <div>
          <h4 className="font-bold text-sm text-ink-primary">Ready to Finalize?</h4>
          <p className="text-xs text-ink-secondary mt-0.5">
            Finalizing commits official attendance records to the institutional database.
            {presentCount > 0 || absentCount > 0 ? ` (${presentCount} Present, ${absentCount} Absent)` : ''}
          </p>
          {!canFinalize && finalizeDisabledReason && (
            <p className="text-xs text-red-600 font-semibold mt-1 flex items-center gap-1">
              <AlertTriangle size={13} />
              {finalizeDisabledReason}
            </p>
          )}
        </div>

        <div className="flex items-center gap-3 w-full sm:w-auto">
          <Link
            to={`/lecturer/sessions/${id}`}
            className="btn-secondary text-xs flex-1 sm:flex-initial text-center"
          >
            Cancel
          </Link>
          <button
            className="btn-primary text-xs py-2.5 px-6 flex-1 sm:flex-initial flex items-center justify-center gap-2"
            disabled={!canFinalize}
            onClick={() => setShowConfirm(true)}
            title={finalizeDisabledReason}
          >
            {confirmMut.isPending ? <Spinner size="sm" /> : <Check size={16} />}
            <span>Confirm & Finalize Attendance</span>
          </button>
        </div>
      </div>

      {/* Confirmation Dialog */}
      {showConfirm && (
        <ConfirmDialog
          title="Confirm & Finalize Official Attendance"
          message={`Are you sure you want to finalize this attendance session? Exactly ${presentCount} students will be marked Present and ${absentCount} will be marked Absent. Finalized records become official institutional data.`}
          onConfirm={() => {
            setShowConfirm(false)
            confirmMut.mutate()
          }}
          onCancel={() => setShowConfirm(false)}
        />
      )}

      {/* Quick Add Student Modal */}
      {showAddStudent && (
        <div className="fixed inset-0 z-50 bg-black/40 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl shadow-xl max-w-md w-full p-6 border border-ink-border">
            <div className="flex items-center justify-between mb-4 pb-3 border-b border-ink-border">
              <div className="flex items-center gap-2">
                <div className="w-8 h-8 rounded-lg bg-forest-50 text-forest flex items-center justify-center">
                  <UserPlus size={18} />
                </div>
                <h3 className="font-bold text-ink-primary">Add Student to Class Roster</h3>
              </div>
              <button
                onClick={() => setShowAddStudent(false)}
                className="text-gray-400 hover:text-gray-600 p-1"
              >
                <X size={18} />
              </button>
            </div>

            <form onSubmit={handleQuickAddStudent} className="space-y-4">
              <div>
                <label className="label">Full Name</label>
                <input
                  type="text"
                  required
                  placeholder="e.g. Aishadipto Biswas"
                  value={newStudentName}
                  onChange={e => setNewStudentName(e.target.value)}
                  className="input text-sm"
                />
              </div>

              <div>
                <label className="label">USN (University Seat Number)</label>
                <input
                  type="text"
                  required
                  placeholder="e.g. 01JST24UCS007"
                  value={newStudentUsn}
                  onChange={e => setNewStudentUsn(e.target.value.toUpperCase())}
                  className="input text-sm uppercase font-mono"
                />
              </div>

              <div className="pt-2 flex justify-end gap-2.5">
                <button
                  type="button"
                  className="btn-secondary text-xs"
                  onClick={() => setShowAddStudent(false)}
                  disabled={addingStudent}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="btn-primary text-xs flex items-center gap-1.5"
                  disabled={addingStudent}
                >
                  {addingStudent ? <Spinner size="sm" /> : <Check size={14} />}
                  <span>Enroll & Assign Student</span>
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}
