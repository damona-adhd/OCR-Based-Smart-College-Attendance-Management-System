import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import {
  FileUp,
  AlertCircle,
  CheckCircle,
  FileText,
  Trash2,
  Edit2,
  Users,
  Building,
  ArrowRight,
  RefreshCw,
  Info,
} from 'lucide-react'
import toast from 'react-hot-toast'
import { PageHeader } from '../../components/ui/PageHeader'
import { Spinner } from '../../components/ui/Spinner'
import { classesApi } from '../../api/classes'
import { rosterApi, type RosterPreviewResponse, type RosterPreviewRow } from '../../api/roster'

export default function RosterImportPage() {
  const [selectedClassId, setSelectedClassId] = useState<number | ''>('')
  const [file, setFile] = useState<File | null>(null)
  const [previewLoading, setPreviewLoading] = useState(false)
  const [importLoading, setImportLoading] = useState(false)
  const [previewData, setPreviewData] = useState<RosterPreviewResponse | null>(null)
  const [editableRows, setEditableRows] = useState<RosterPreviewRow[]>([])
  const [editingIndex, setEditingIndex] = useState<number | null>(null)
  const [editUsn, setEditUsn] = useState('')
  const [editName, setEditName] = useState('')
  const [importSummary, setImportSummary] = useState<{ imported: number; skipped: number; message: string } | null>(null)

  // Fetch classes for assignment dropdown
  const { data: classes = [], isLoading: classesLoading } = useQuery({
    queryKey: ['classes-list'],
    queryFn: () => classesApi.list(),
  })

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selected = e.target.files?.[0]
    if (selected) {
      if (!selected.name.toLowerCase().endsWith('.pdf')) {
        toast.error('Please upload a PDF document (.pdf)')
        return
      }
      setFile(selected)
      setPreviewData(null)
      setEditableRows([])
      setImportSummary(null)
    }
  }

  const handlePreview = async () => {
    if (!file) {
      toast.error('Please select a roster PDF file first.')
      return
    }
    setPreviewLoading(true)
    setImportSummary(null)
    try {
      const res = await rosterApi.preview(file, selectedClassId ? Number(selectedClassId) : undefined)
      setPreviewData(res)
      setEditableRows(res.rows)
      if (res.rows.length === 0) {
        toast.error(res.note || 'No valid student records could be extracted from this PDF.')
      } else {
        toast.success(`Extracted ${res.total_extracted} records (${res.new_count} new)`)
      }
    } catch (err: any) {
      toast.error(err.response?.data?.detail || 'Failed to inspect and preview PDF roster.')
    } finally {
      setPreviewLoading(false)
    }
  }

  const handleStartEdit = (index: number) => {
    setEditingIndex(index)
    setEditUsn(editableRows[index].usn)
    setEditName(editableRows[index].full_name)
  }

  const handleSaveEdit = (index: number) => {
    const updated = [...editableRows]
    updated[index] = {
      ...updated[index],
      usn: editUsn.trim().toUpperCase(),
      full_name: editName.trim(),
    }
    setEditableRows(updated)
    setEditingIndex(null)
    toast.success('Row updated')
  }

  const handleRemoveRow = (index: number) => {
    const updated = editableRows.filter((_, i) => i !== index)
    setEditableRows(updated)
    toast.success('Row removed from import batch')
  }

  const handleCommitImport = async () => {
    if (!selectedClassId) {
      toast.error('Please select a target class/section before importing.')
      return
    }

    const newRowsToImport = editableRows.filter(r => r.status === 'new')
    if (newRowsToImport.length === 0) {
      toast.error('No new records to import in this batch.')
      return
    }

    const confirmCommit = window.confirm(
      `Are you sure you want to commit ${newRowsToImport.length} new student records to the selected class in PostgreSQL?`
    )
    if (!confirmCommit) return

    setImportLoading(true)
    try {
      const res = await rosterApi.commitImport(
        Number(selectedClassId),
        newRowsToImport.map(r => ({ usn: r.usn, full_name: r.full_name }))
      )
      setImportSummary({
        imported: res.imported_count,
        skipped: res.skipped_count,
        message: res.message,
      })
      toast.success(res.message)
      // Mark imported rows as existing
      setEditableRows(prev =>
        prev.map(r => (r.status === 'new' ? { ...r, status: 'existing', notes: 'Imported in this session' } : r))
      )
    } catch (err: any) {
      toast.error(err.response?.data?.detail || 'Failed to commit roster import.')
    } finally {
      setImportLoading(false)
    }
  }

  return (
    <div>
      <PageHeader
        title="PDF Student Roster Import"
        subtitle="Import student rosters directly from digitally generated college PDFs with duplicate prevention."
      />

      {/* Target Class Selection & File Upload Card */}
      <div className="card mb-8">
        <h3 className="text-base font-bold text-ink-primary mb-4 flex items-center gap-2">
          <FileUp size={20} className="text-forest" />
          <span>Upload College Student Register PDF</span>
        </h3>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 items-end">
          {/* Target Class dropdown */}
          <div>
            <label className="label" htmlFor="target-class">
              Target Class & Section <span className="text-coral">*</span>
            </label>
            {classesLoading ? (
              <Spinner size="sm" />
            ) : (
              <select
                id="target-class"
                className="input"
                value={selectedClassId}
                onChange={(e) => setSelectedClassId(e.target.value ? Number(e.target.value) : '')}
              >
                <option value="">-- Select Class / Section --</option>
                {classes.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.name} — Sem {c.semester} (Sec {c.section || 'A'}) [{c.academic_year}]
                  </option>
                ))}
              </select>
            )}
            <p className="mt-1 text-xs text-ink-secondary">
              Selected class assigns the student's department, semester, and academic year automatically.
            </p>
          </div>

          {/* File Picker */}
          <div>
            <label className="label" htmlFor="roster-pdf">
              Select Roster PDF File <span className="text-coral">*</span>
            </label>
            <input
              id="roster-pdf"
              type="file"
              accept=".pdf,application/pdf"
              className="input file:mr-4 file:py-1 file:px-3 file:rounded-lg file:border-0 file:text-xs file:font-semibold file:bg-forest-100 file:text-forest hover:file:bg-forest-200 cursor-pointer"
              onChange={handleFileChange}
            />
            {file && (
              <p className="mt-1 text-xs text-forest font-medium">
                Selected: {file.name} ({(file.size / 1024).toFixed(1)} KB)
              </p>
            )}
          </div>
        </div>

        <div className="mt-6 pt-5 border-t border-ink-border flex flex-wrap items-center justify-between gap-4">
          <div className="flex items-center gap-2 text-xs text-ink-secondary">
            <Info size={16} className="text-forest" />
            <span>Direct PyMuPDF text layer extraction is applied without unreliable external OCR.</span>
          </div>

          <button
            type="button"
            disabled={!file || previewLoading}
            onClick={handlePreview}
            className="btn-primary"
          >
            {previewLoading ? (
              <>
                <Spinner size="sm" />
                <span>Inspecting Roster PDF...</span>
              </>
            ) : (
              <>
                <FileText size={16} />
                <span>Extract & Preview Roster</span>
              </>
            )}
          </button>
        </div>
      </div>

      {/* Import Success Banner */}
      {importSummary && (
        <div className="bg-[#EAF5F0] border border-status-present/30 rounded-2xl p-5 mb-8 flex items-start gap-3">
          <CheckCircle size={22} className="text-status-present shrink-0 mt-0.5" />
          <div>
            <h4 className="font-bold text-status-present text-sm">Import Completed Successfully</h4>
            <p className="text-sm text-ink-primary mt-1">{importSummary.message}</p>
            <p className="text-xs text-ink-secondary mt-1">
              New students have been enrolled in the database. De-duplication guaranteed no records were overwritten.
            </p>
          </div>
        </div>
      )}

      {/* Preview Section */}
      {previewData && (
        <div className="space-y-6">
          {/* Inspection Metadata & Stats */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="card p-4">
              <span className="text-xs text-ink-secondary font-medium uppercase tracking-wider">Total Extracted</span>
              <p className="text-2xl font-bold text-ink-primary mt-1">{editableRows.length}</p>
              <span className="text-xs text-ink-secondary">{previewData.page_count} PDF page(s)</span>
            </div>

            <div className="card p-4">
              <span className="text-xs text-status-present font-medium uppercase tracking-wider">New Students</span>
              <p className="text-2xl font-bold text-status-present mt-1">
                {editableRows.filter((r) => r.status === 'new').length}
              </p>
              <span className="text-xs text-ink-secondary">Ready to import</span>
            </div>

            <div className="card p-4">
              <span className="text-xs text-ink-secondary font-medium uppercase tracking-wider">Already in Database</span>
              <p className="text-2xl font-bold text-ink-primary mt-1">
                {editableRows.filter((r) => r.status === 'existing').length}
              </p>
              <span className="text-xs text-ink-secondary">Will be skipped safely</span>
            </div>

            <div className="card p-4">
              <span className="text-xs text-status-absent font-medium uppercase tracking-wider">Invalid / Duplicates</span>
              <p className="text-2xl font-bold text-status-absent mt-1">
                {editableRows.filter((r) => r.status === 'invalid').length}
              </p>
              <span className="text-xs text-ink-secondary">Requires correction</span>
            </div>
          </div>

          {/* PDF Inspection Note */}
          <div className="bg-white rounded-2xl p-4 border border-ink-border text-sm flex items-center justify-between">
            <div className="flex items-center gap-2">
              <span className="badge-forest uppercase text-xs">{previewData.kind}</span>
              <span className="text-ink-secondary">{previewData.note}</span>
            </div>
            {editableRows.filter((r) => r.status === 'new').length > 0 && (
              <button
                type="button"
                disabled={importLoading || !selectedClassId}
                onClick={handleCommitImport}
                className="btn-primary text-sm py-2 px-4 shadow-sm"
              >
                {importLoading ? (
                  <>
                    <Spinner size="sm" />
                    <span>Importing to Database...</span>
                  </>
                ) : (
                  <>
                    <Users size={16} />
                    <span>Commit {editableRows.filter((r) => r.status === 'new').length} New Students</span>
                  </>
                )}
              </button>
            )}
          </div>

          {/* Editable Preview Table */}
          <div className="card p-0 overflow-hidden">
            <div className="px-6 py-4 border-b border-ink-border flex items-center justify-between">
              <div>
                <h4 className="font-bold text-ink-primary text-base">Extracted Student Preview Table</h4>
                <p className="text-xs text-ink-secondary">
                  Review extracted student names and USNs. You can edit or remove rows before committing.
                </p>
              </div>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-left">
                <thead>
                  <tr>
                    <th className="table-th w-16">#</th>
                    <th className="table-th">USN</th>
                    <th className="table-th">Student Full Name</th>
                    <th className="table-th">Status</th>
                    <th className="table-th">Notes</th>
                    <th className="table-th text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-ink-border/60">
                  {editableRows.length === 0 ? (
                    <tr>
                      <td colSpan={6} className="py-8 text-center text-sm text-ink-secondary">
                        No rows to preview.
                      </td>
                    </tr>
                  ) : (
                    editableRows.map((row, idx) => (
                      <tr key={idx} className="hover:bg-gray-50/50">
                        <td className="table-td text-ink-secondary">{idx + 1}</td>
                        <td className="table-td font-mono font-semibold">
                          {editingIndex === idx ? (
                            <input
                              type="text"
                              className="input py-1 px-2 text-xs"
                              value={editUsn}
                              onChange={(e) => setEditUsn(e.target.value)}
                            />
                          ) : (
                            row.usn
                          )}
                        </td>
                        <td className="table-td">
                          {editingIndex === idx ? (
                            <input
                              type="text"
                              className="input py-1 px-2 text-xs"
                              value={editName}
                              onChange={(e) => setEditName(e.target.value)}
                            />
                          ) : (
                            row.full_name
                          )}
                        </td>
                        <td className="table-td">
                          {row.status === 'new' && <span className="badge-green">New Record</span>}
                          {row.status === 'existing' && <span className="badge-gray">Existing</span>}
                          {row.status === 'invalid' && <span className="badge-red">Invalid</span>}
                        </td>
                        <td className="table-td text-xs text-ink-secondary">{row.notes || '—'}</td>
                        <td className="table-td text-right">
                          <div className="inline-flex items-center gap-1">
                            {editingIndex === idx ? (
                              <button
                                type="button"
                                onClick={() => handleSaveEdit(idx)}
                                className="px-2 py-1 text-xs font-semibold rounded-lg bg-forest text-white"
                              >
                                Save
                              </button>
                            ) : (
                              <button
                                type="button"
                                onClick={() => handleStartEdit(idx)}
                                className="p-1.5 text-ink-secondary hover:text-forest rounded-lg hover:bg-gray-100"
                                title="Edit Row"
                              >
                                <Edit2 size={14} />
                              </button>
                            )}
                            <button
                              type="button"
                              onClick={() => handleRemoveRow(idx)}
                              className="p-1.5 text-ink-secondary hover:text-status-absent rounded-lg hover:bg-gray-100"
                              title="Remove Row"
                            >
                              <Trash2 size={14} />
                            </button>
                          </div>
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
