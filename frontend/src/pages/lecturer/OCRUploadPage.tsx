import { useState, useRef } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useQuery, useMutation } from '@tanstack/react-query'
import toast from 'react-hot-toast'
import { Upload, ImageIcon, RefreshCw, X, FileText } from 'lucide-react'
import { PageHeader } from '../../components/ui/PageHeader'
import { Spinner } from '../../components/ui/Spinner'
import { attendanceApi } from '../../api/attendance'
import { ocrApi } from '../../api/ocr'

const MAX_SIZE_MB = 10

export default function OCRUploadPage() {
  const { sessionId } = useParams<{ sessionId: string }>()
  const navigate = useNavigate()
  const id = Number(sessionId)

  const fileInputRef = useRef<HTMLInputElement>(null)
  const [file, setFile] = useState<File | null>(null)
  const [preview, setPreview] = useState<string | null>(null)
  const [uploadDone, setUploadDone] = useState(false)

  const { data: session } = useQuery({
    queryKey: ['session', id], queryFn: () => attendanceApi.getSession(id)
  })

  const uploadMut = useMutation({
    mutationFn: (f: File) => ocrApi.uploadImage(id, f),
    onSuccess: () => { toast.success('Image uploaded'); setUploadDone(true) },
    onError: (e: any) => toast.error(e.response?.data?.detail || 'Upload failed'),
  })

  const processMut = useMutation({
    mutationFn: () => ocrApi.processOCR(id),
    onSuccess: (result) => {
      toast.success('OCR processing complete')
      navigate(`/lecturer/sessions/${id}/ocr-review`, { state: { result } })
    },
    onError: (e: any) => {
      const detail = e.response?.data?.detail || 'OCR processing failed'
      if (e.response?.status === 500) {
        toast.error('OCR failed — Tesseract may not be installed on this server. You can still enter attendance manually.')
      } else {
        toast.error(detail)
      }
    },
  })

  const handleFileSelect = (f: File) => {
    const isPdf = f.type === 'application/pdf' || f.name.toLowerCase().endsWith('.pdf')
    const isImage = ['image/jpeg', 'image/jpg', 'image/png'].includes(f.type)
    if (!isPdf && !isImage) {
      toast.error('Only PDF, JPG, and PNG register documents are allowed')
      return
    }
    if (f.size > MAX_SIZE_MB * 1024 * 1024) {
      toast.error(`File too large. Max ${MAX_SIZE_MB}MB`)
      return
    }
    setFile(f)
    if (isImage) {
      setPreview(URL.createObjectURL(f))
    } else {
      setPreview('pdf')
    }
    setUploadDone(false)
  }

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault()
    const f = e.dataTransfer.files[0]
    if (f) handleFileSelect(f)
  }

  return (
    <div>
      <PageHeader title="Upload Attendance Register" subtitle={session ? `Session: ${session.attendance_date}` : ''} />

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Upload area */}
        <div className="card">
          <h3 className="font-semibold mb-4">Select Register Image</h3>

          {!preview ? (
            <div
              className="border-2 border-dashed border-gray-300 rounded-xl p-10 text-center cursor-pointer hover:border-primary-400 hover:bg-primary-50 transition-colors"
              onDrop={handleDrop}
              onDragOver={e => e.preventDefault()}
              onClick={() => fileInputRef.current?.click()}
            >
              <ImageIcon size={40} className="text-gray-300 mx-auto mb-3" />
              <p className="text-sm font-medium text-gray-600">Drop an attendance register image or PDF here or click to browse</p>
              <p className="text-xs text-gray-400 mt-1">PDF, JPG, PNG — max {MAX_SIZE_MB}MB</p>
              <input
                ref={fileInputRef}
                type="file"
                accept="image/jpeg,image/jpg,image/png,application/pdf,.pdf"
                className="hidden"
                onChange={e => e.target.files?.[0] && handleFileSelect(e.target.files[0])}
              />
            </div>
          ) : (
            <div className="relative">
              {preview === 'pdf' ? (
                <div className="p-8 border border-ink-border rounded-xl bg-gray-50 flex items-center gap-4">
                  <div className="w-12 h-12 rounded-xl bg-forest-100 flex items-center justify-center">
                    <FileText size={24} className="text-forest" />
                  </div>
                  <div>
                    <p className="text-sm font-bold text-ink-primary">{file?.name}</p>
                    <p className="text-xs text-ink-secondary">{((file?.size || 0) / 1024).toFixed(1)} KB PDF Document</p>
                  </div>
                </div>
              ) : (
                <img src={preview} alt="Register preview" className="w-full rounded-xl border border-gray-200 max-h-80 object-contain" />
              )}
              <button
                className="absolute top-2 right-2 p-1 bg-white rounded-full shadow hover:bg-gray-100"
                onClick={() => { setFile(null); setPreview(null); setUploadDone(false) }}
              >
                <X size={16} />
              </button>
            </div>
          )}

          {file && !uploadDone && (
            <div className="mt-4">
              <p className="text-xs text-gray-500 mb-2">{file.name} ({(file.size / 1024).toFixed(0)} KB)</p>
              <button
                className="btn-primary w-full"
                onClick={() => uploadMut.mutate(file)}
                disabled={uploadMut.isPending}
              >
                {uploadMut.isPending ? <><Spinner size="sm" />Uploading...</> : <><Upload size={16} />Upload Image</>}
              </button>
            </div>
          )}

          {uploadDone && (
            <div className="mt-4 p-3 bg-green-50 rounded-lg text-sm text-green-700 font-medium text-center">
              ✓ Image uploaded successfully
            </div>
          )}
        </div>

        {/* Instructions & Process */}
        <div className="space-y-4">
          <div className="card">
            <h3 className="font-semibold mb-3">Tips for Best Results</h3>
            <ul className="space-y-2 text-sm text-gray-600">
              <li className="flex gap-2"><span className="text-green-500">✓</span> Use good lighting</li>
              <li className="flex gap-2"><span className="text-green-500">✓</span> Keep the image flat and unfolded</li>
              <li className="flex gap-2"><span className="text-green-500">✓</span> Ensure USN/roll numbers are legible</li>
              <li className="flex gap-2"><span className="text-green-500">✓</span> Avoid blurry or rotated images</li>
              <li className="flex gap-2"><span className="text-yellow-500">⚠</span> OCR results require your review before finalization</li>
              <li className="flex gap-2"><span className="text-yellow-500">⚠</span> Attendance status will not be auto-assigned</li>
            </ul>
          </div>

          {uploadDone && (
            <div className="card">
              <h3 className="font-semibold mb-3">Ready to Process</h3>
              <p className="text-sm text-gray-600 mb-4">
                Click the button below to extract student information from the image using OCR. You will then review and confirm the results.
              </p>
              <button
                className="btn-primary w-full"
                onClick={() => processMut.mutate()}
                disabled={processMut.isPending}
              >
                {processMut.isPending
                  ? <><Spinner size="sm" />Processing OCR...</>
                  : <><RefreshCw size={16} />Process with OCR</>}
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
