import React, {useEffect, useState} from "react";
import List, {ActionDataInterface} from "../components/List";
import toLower from "lodash/toLower";
import cloneDeep from "lodash/cloneDeep";
import {useNavigate} from "react-router-dom";
import DeleteIcon from "@mui/icons-material/Delete";
import FactCheckIcon from '@mui/icons-material/FactCheck';
import {setModule} from "../reducers/module";
import {useAppDispatch} from "../app/hooks";
import {modules} from "../modules";
import {ReviewListRoute} from "./routes";
import {fetchData, postData} from "../utils/Requests";
import Loading from "../components/Loading";
import AlertDialog from '../components/AlertDialog'

const READ_ONLY_SESSION_STATUSES = ['Canceled', 'Done', 'Reviewing']
const DELETE_UPLOAD_SESSION_URL = '/api/delete-upload-session'

interface UploadSessionData {
  id: number,
  upload: string,
  type: string,
  upload_date: Date,
  uploaded_by: string,
  status: string
}

export default function UploadSessionList() {

  const [loading, setLoading] = useState<boolean>(true)
  const [sessionsData, setSessionsData] = useState<any[]>([])
  const [allData, setAllData] = useState<any[]>()
  const [selectedSession, setSelectedSession] = useState<any>(null)
  const [confirmationOpen, setConfirmationOpen] = useState<boolean>(false)
  const [confirmationText, setConfirmationText] = useState<string>('')
  const [deleteButtonDisabled, setDeleteButtonDisabled] = useState<boolean>(false)
  const navigate = useNavigate()
  const dispatch = useAppDispatch()

  const actionReviewButton: ActionDataInterface = {
    field: '',
    name: 'Review',
    getName: (data: any) => {
        if (data.status !== 'Reviewing') {
            return 'Review is not available'
        }
        return 'Delete'
    },
    icon: <FactCheckIcon />,
    isDisabled: (data: UploadSessionData) : boolean => {
      return data.status !== 'Reviewing'
    },
    onClick: (data: UploadSessionData) => {
      // Go to review page
      navigate(`${ReviewListRoute.path}?upload=${data.upload}`)
    }
  }

  const actionDeleteButton: ActionDataInterface = {
    field: '',
    name: 'Delete',
    getName: (data: any) => {
        if (data.status === 'Done') {
            return 'Cannot removed processed upload'
        } else if (data.status === 'Processing') {
            return 'Cannot removed ongoing upload'
        }
        return 'Delete'
    },
    color: 'error',
    icon: <DeleteIcon />,
    actionGroup: 'delete',
    isDisabled: (data: UploadSessionData) : boolean => {
      return ['Done', 'Processing'].includes(data.status)
    },
    onClick: (data: UploadSessionData) => {
      setSelectedSession(data)
      setConfirmationText(
        `Are you sure you want to delete ${data.upload}?`)
      setConfirmationOpen(true)
    }
  }

  const fetchUploadSession = () => {
    fetchData('/api/upload-sessions/').then(
      response => {
        setAllData(cloneDeep(response.data))
        let _sessionData = response.data.map((responseData: any) => {
          delete responseData['form']
          return responseData
        })
        setSessionsData(_sessionData)
        setLoading(false)
      }
    )
  }

  useEffect(() => {
    fetchUploadSession()
  }, [])

  const handleDeleteClick = () => {
    setDeleteButtonDisabled(true)
    postData(
      `${DELETE_UPLOAD_SESSION_URL}/${selectedSession.id}`, {}
    ).then(
      response => {
        setDeleteButtonDisabled(false)
        fetchUploadSession()
        setConfirmationOpen(false)
      }
    ).catch(error => {
      setDeleteButtonDisabled(false)
      alert('Error deleting upload session')
    })
  }

  const handleClose = () => {
    setConfirmationOpen(false)
  }

  const handleRowClick = (rowData: string[], rowMeta: { dataIndex: number, rowIndex: number }) => {
    const row = allData.find(sessionData => sessionData.id === rowData[0])
    let moduleName = toLower(row.type.replace(' ', '_'))
    if (!moduleName) {
      moduleName = modules[0]
    } 
    dispatch(setModule(moduleName))
    navigate(`/${moduleName}/upload_wizard/${row.form}`)
  }

  return (
    <div className="AdminContentMain main-data-list">
      <AlertDialog open={confirmationOpen} alertClosed={handleClose}
          alertConfirmed={handleDeleteClick}
          alertLoading={deleteButtonDisabled}
          alertDialogTitle={'Delete upload session'}
          alertDialogDescription={confirmationText}
          confirmButtonText='Delete'
          confirmButtonProps={{color: 'error', autoFocus: true}}
      />
    {loading ? <Loading/> :
    <List
      pageName={'Uploads'}
      listUrl={''}
      initData={sessionsData}
      selectionChanged={null}
      onRowClick={handleRowClick}
      actionData={[actionReviewButton, actionDeleteButton]}
    />}
    </div>
  )
}
