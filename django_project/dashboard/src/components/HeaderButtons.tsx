import React, {useEffect, useState} from 'react';
import {ThemeButton, AddButton, EditButton, CancelButton, WarningButton} from "./Elements/Buttons";
import {Link, useNavigate, useSearchParams} from "react-router-dom";
import axios from "axios";
import toLower from "lodash/toLower";
import Divider from '@mui/material/Divider';
import GradingIcon from '@mui/icons-material/Grading';
import Typography from '@mui/material/Typography';
import {postData} from "../utils/Requests";
import {currentModule, setModule} from "../reducers/module";
import {toggleIsBatchReview, setPendingReviews, setCurrentReview, onBatchReviewSubmitted} from "../reducers/reviewAction";
import {RootState} from "../app/store";
import {useAppDispatch, useAppSelector} from "../app/hooks";
import {modules} from "../modules";
import AlertDialog from './AlertDialog';
import AlertMessage from './AlertMessage';
import CircularProgress from '@mui/material/CircularProgress';
import {
  UserAddRoute,
  DatasetCreateRoute,
  DatasetRoute,
  UserListRoute,
  GroupListRoute,
  GroupDetailRoute,
  ViewCreateRoute,
  ViewListRoute,
  ViewSyncStatusRoute,
  ReviewListRoute,
  UploadSessionListRoute
} from "../views/routes";
import Dataset from '../models/dataset';
import { ActiveBatchReview } from '../models/review';
import {setPollInterval, FETCH_INTERVAL_JOB} from "../reducers/notificationPoll";

interface UploadDataButtonInterface {
  next?: any,
  moreActions?: React.ElementType
}

const MoreActionsElement = (Component: React.ElementType, givenProps: any) => {
  return <Component {...givenProps} />
}

const CAN_ADD_UPLOAD_URL = '/api/can-add-upload/'
const ADD_UPLOAD_SESSION_URL = '/api/add-upload-session/'
const FETCH_PENDING_REVIEWS_URL = '/api/review/batch/uploads/'
const FETCH_CURRENT_REVIEW_URL = '/api/review/batch/identifier/'
const SUBMIT_BATCH_REVIEW_URL = '/api/review/batch/'
const CONFIRM_RESET_SESSION_URL = '/api/reset-upload-session/'
const LOAD_UPLOAD_SESSION_DETAIL_URL = '/api/upload-session/'

export const UploadDataButton = (props: UploadDataButtonInterface) => {
  const [canUpload, setCanUpload] = useState<boolean>(false)
  const [activeUpload, setActiveUpload] = useState<any>(null)
  const [searchParams, setSearchParams] = useSearchParams()
  const [dataset, setDataset] = useState<Dataset>(null)
  const navigate = useNavigate()
  const dispatch = useAppDispatch()
  let currentModuleName = useAppSelector(currentModule)

  useEffect(() => {
    axios.get(`${CAN_ADD_UPLOAD_URL}${searchParams.get('id')}/`).then((response) => {
      if (response.data) {
        setCanUpload(response.data['can_upload'])
        setDataset(response.data['dataset'])
        if (response.data['active_upload']) {
          setActiveUpload(response.data['active_upload'])
        }
      }
    })
  }, [searchParams])

  const addButtonClick = () => {
    setCanUpload(false)
    postData(`${ADD_UPLOAD_SESSION_URL}${searchParams.get('id')}/`, {
      'source': '',
      'description': '',
      'dataset': searchParams.get('id')
    }).then( response => {
      if (response.data.session_id) {
        if (props.next) {
          navigate(`${props.next}?session=${response.data.session_id}&dataset=${searchParams.get('id')}&step=0`)
        } else {
          navigate(`/upload_wizard?session=${response.data.session_id}&dataset=${searchParams.get('id')}&step=0`)
        }
      }
    }).catch(error => {
      console.log('error ', error)
      if (error.response) {
          let _error_message = 'Error create new upload!'
          if (error.response.status == 403) {
            // TODO: use better way to handle 403
            navigate('/invalid_permission')
          } else if (error.response.data) {
            let _error = error.response.data
            if (_error && 'detail' in _error) {
              _error_message = _error['detail']
            }
            alert(_error_message)
          }
      } else {
        alert('Error adding new data.')
        setCanUpload(true)
      }
    })
  }

  const activeUploadButtonClick = () => {
    if (activeUpload.status === 'Reviewing') {
      navigate(ReviewListRoute.path)
    } else if (activeUpload.form) {
      let moduleName = toLower(activeUpload.type.replace(' ', '_'))
      if (!moduleName) {
        moduleName = modules[0]
      }
      dispatch(setModule(moduleName))
      navigate(`/${moduleName}/upload_wizard/${activeUpload.form}`)
    } else {
      navigate(UploadSessionListRoute.path)
    }
  }
  
  

  return (
    <div style={{display:'flex', flexDirection: 'row', alignItems: 'center'}}>
        { activeUpload && activeUpload.id && 
          <EditButton disabled={!dataset.is_active} text={'Active Upload'} variant={'primary'} onClick={activeUploadButtonClick} />
        }
        <AddButton disabled={!canUpload || !dataset.is_active} text={'Add data'} variant={'secondary'}
               onClick={addButtonClick}/>
        { props.moreActions ? <Divider orientation='vertical' flexItem={true} sx={{marginLeft: '10px'}} /> : null }
        { props.moreActions ? MoreActionsElement(props.moreActions, {
          dataset: dataset
        }) : null }
    </div>
  )
}

export const CreateDatasetButton = () => {
  const [canAddDataset, setCanAddDataset] = useState(false)

  useEffect(() => {
    axios.get(`/api/check-user-write-permission/`).then((response) => {
      if (response.data) {
        setCanAddDataset(response.data['can_create_dataset'])
      }
    })
  }, [])

  return (
    <Link to={DatasetCreateRoute.path} >
      <AddButton disabled={!canAddDataset} text={'Create Dataset'} variant={'secondary'}/>
    </Link>
  )
}

export const AddUserButton = () => {
  const [canAddUser, setCanAddUser] = useState((window as any).is_admin)

  return (
    <Link to={UserAddRoute.path} >
      <AddButton disabled={!canAddUser} text={'Add User'} variant={'secondary'}/>
    </Link>
  )
}

export const AddGroupButton = () => {
  return (
    <Link to={`${GroupDetailRoute.path}?id=${0}&tab=${0}`}>
      <AddButton text={'Add Group'} variant={'secondary'}/>
    </Link>
  )
}

export const AddViewButton = () => {
  const [canAddView, setCanAddView] = useState(false)

  useEffect(() => {
    axios.get(`/api/check-user-write-permission/`).then((response) => {
      if (response.data) {
        setCanAddView(response.data['can_create_datasetview'])
      }
    })
  }, [])

  return (<Link to={ViewCreateRoute.path}>
    <AddButton disabled={!canAddView} text={'Add View'} variant={'secondary'}/>
  </Link>)
}

export const ReviewActionButtons = () => {
  const dispatch = useAppDispatch()
  const navigate = useNavigate()
  const isBatchReviewAvailable = useAppSelector((state: RootState) => state.reviewAction.isBatchReviewAvailable)
  const isBatchReview = useAppSelector((state: RootState) => state.reviewAction.isBatchReview)
  const selectedReviews = useAppSelector((state: RootState) => state.reviewAction.selectedReviews)
  const currentReview = useAppSelector((state: RootState) => state.reviewAction.currentReview)
  const [alertOpen, setAlertOpen] = useState<boolean>(false)
  const [alertDialogTitle, setAlertDialogTitle] = useState<string>('')
  const [alertDialogDescription, setAlertDialogDescription] = useState<string>('')
  const [alertLoading, setAlertLoading] = useState<boolean>(false)
  const [isApprove, setIsApprove] = useState<boolean>(true)
  const [confirmMessage, setConfirmMessage] = useState<string>('')
  const [currentInterval, setCurrentInterval] = useState<any>(null)

  const fetchCurrentReview = () => {
    axios.get(`${FETCH_CURRENT_REVIEW_URL}0/`).then((response) => {
      if (response.data) {
        let _batchReview = response.data as ActiveBatchReview
        if (currentReview.id && _batchReview.id === 0) {
          // batch review has finished, refresh review list
          dispatch(onBatchReviewSubmitted())
        }
        dispatch(setCurrentReview(_batchReview))
      }
    })
  }

  const fetchPendingReviews = () => {
    axios.get(`${FETCH_PENDING_REVIEWS_URL}`).then((response) => {
      if (response.data) {
        dispatch(setPendingReviews(response.data))
      }
      dispatch(toggleIsBatchReview())
    })
  }

  const onToggleBatchReview = () => {
    if (isBatchReview) {
      dispatch(toggleIsBatchReview())
    } else {
      fetchPendingReviews()
    }
  }

  useEffect(() => {
    fetchCurrentReview()
  }, [])

  useEffect(() => {
    if (!isBatchReviewAvailable) {
      if (currentInterval) {
          clearInterval(currentInterval)
          setCurrentInterval(null)
      }
      const interval = setInterval(() => {
        fetchCurrentReview()
      }, 1500)
      setCurrentInterval(interval)
      return () => clearInterval(interval)
    }
  }, [isBatchReviewAvailable])

  const alertConfirmed = () => {
    const data = {
      upload_entities: selectedReviews,
      is_approve: isApprove
    }
    setAlertLoading(true)
    postData(`${SUBMIT_BATCH_REVIEW_URL}`, data).then(
        response => {
          setAlertLoading(false)
          setAlertOpen(false)
          setConfirmMessage('Successfully submitting batch review. Your request will be processed in the background.')
          dispatch(toggleIsBatchReview())
          fetchCurrentReview()
          dispatch(onBatchReviewSubmitted())
          // trigger to fetch notification frequently
          dispatch(setPollInterval(FETCH_INTERVAL_JOB))
        }
      ).catch(error => {
            setAlertLoading(false)
            setAlertOpen(false)
            console.log('error ', error)
            if (error.response) {
                if (error.response.status == 403) {
                  // TODO: use better way to handle 403
                  navigate('/invalid_permission')
                }
            } else {
                setConfirmMessage('An error occurred. Please try it again later')
            }
    })
  }

  const handleAlertCancel = () => {
    setAlertOpen(false)
  }

  const onBatchApproveClick = () => {
    setIsApprove(true)
    setAlertDialogTitle('Batch Approve')
    setAlertDialogDescription(`Are you sure you want to approve ${selectedReviews.length} entities?`)
    setAlertOpen(true)
  }

  const onBatchRejectClick = () => {
    setIsApprove(false)
    setAlertDialogTitle('Batch Reject')
    setAlertDialogDescription(`Are you sure you want to reject ${selectedReviews.length} entities?`)
    setAlertOpen(true)
  }

  return (
    <div style={{display:'flex', flexDirection: 'row', alignItems: 'center'}}>
      <AlertMessage message={confirmMessage} onClose={() => setConfirmMessage('')} />
      <AlertDialog open={alertOpen} alertClosed={handleAlertCancel}
                 alertConfirmed={alertConfirmed}
                 alertLoading={alertLoading}
                 alertDialogTitle={alertDialogTitle}
                 alertDialogDescription={alertDialogDescription} />
      { !isBatchReviewAvailable && (
        <div style={{display:'flex', flexDirection: 'row', alignItems: 'center'}} className='AdminContentText'>
          <CircularProgress size={18} sx={{marginRight: '10px'}} />
          <Typography variant={'subtitle2'} >Batch Review: {currentReview.progress}</Typography>
        </div>
      )}
      { isBatchReviewAvailable && (
        <div style={{display:'flex', flexDirection: 'row', alignItems: 'center'}}>
          { !isBatchReview && (
            <ThemeButton icon={<GradingIcon />} disabled={!isBatchReviewAvailable} title={'Batch Review'} variant={'secondary'} onClick={onToggleBatchReview}/>
          )}
          { isBatchReview && (
            <Typography variant={'subtitle2'} >{selectedReviews.length} selected</Typography>
          )}
          { isBatchReview && (
            <AddButton disabled={selectedReviews.length === 0} text={'Approve'} variant={'secondary'} useIcon={false} additionalClass={'MuiButtonMedium'} onClick={onBatchApproveClick}/>
          )}
          { isBatchReview && (
            <WarningButton disabled={selectedReviews.length === 0} text={'Reject'} useIcon={false} additionalClass={'MuiButtonMedium'} onClick={onBatchRejectClick}/>
          )}
          { isBatchReview && (
            <CancelButton onClick={onToggleBatchReview} />
          )}
        </div>
      )}
    </div>    
  )
}

export const CancelActiveUploadButton = () => {
  const navigate = useNavigate()
  const [searchParams, setSearchParams] = useSearchParams()
  const [isActiveUpload, setIsActiveUpload] = useState(false)
  const [moduleName, setModuleName] = useState('')
  const [alertOpen, setAlertOpen] = useState<boolean>(false)
  const [alertDialogTitle, setAlertDialogTitle] = useState<string>('')
  const [alertDialogDescription, setAlertDialogDescription] = useState<string>('')
  const [alertLoading, setAlertLoading] = useState<boolean>(false)
  const [confirmMessage, setConfirmMessage] = useState<string>('')

  useEffect(() => {
    fetchUploadSessionStatus()
  }, [])

  const fetchUploadSessionStatus = () => {
    const uploadSession = searchParams.get('session')
    if (uploadSession) {
      // pull the source/description from saved session
      axios.get(LOAD_UPLOAD_SESSION_DETAIL_URL + uploadSession).then(
        response => {
          setModuleName(toLower(response.data.module_name.replace(' ', '_')))
          setIsActiveUpload(!response.data.is_read_only)
        }, error => {
          console.log(error)
        })
    }
  }

  const redirectAfterCancelled = () => {
    setTimeout(() => {
      const datasetId = searchParams.get('dataset')
      navigate(`/${moduleName}/dataset_entities?id=${datasetId}`)
  }, 3000)
  }

  const alertConfirmed = () => {
    setAlertLoading(true)
    postData(`${CONFIRM_RESET_SESSION_URL}${searchParams.get('session')}/${searchParams.get('step')}/?cancel=true`, {}).then(
      response => {
        setAlertLoading(false)
        setAlertOpen(false)
        setConfirmMessage('The upload has been cancelled, redirecting...')
        redirectAfterCancelled()
      }
    ).catch(error => {
      setAlertLoading(false)
      setAlertOpen(false)
      alert('There is something wrong, please try again later')
    })
  }

  const handleAlertCancel = () => {
    setAlertOpen(false)
  }

  const cancelActiveUpload = () => {
    setAlertDialogTitle('Cancel Upload')
    setAlertDialogDescription(`Are you sure you want to cancel current upload?`)
    setAlertOpen(true)
  }

  return (
    <div style={{display:'flex', flexDirection: 'row', alignItems: 'center'}}>
      <AlertMessage message={confirmMessage} onClose={() => setConfirmMessage('')} />
      <AlertDialog open={alertOpen} alertClosed={handleAlertCancel}
                 alertConfirmed={alertConfirmed}
                 alertLoading={alertLoading}
                 alertDialogTitle={alertDialogTitle}
                 alertDialogDescription={alertDialogDescription} />
      { isActiveUpload &&
        <CancelButton onClick={cancelActiveUpload} useIcon={false} text='Cancel Upload' />
      }
    </div>
  )

}

export interface HeaderButtonsInterface {
  path: string,
  element: JSX.Element
}

export const headerButtons: HeaderButtonsInterface[] = [
  {
    path: '/dataset_entities',
    element: <UploadDataButton/>
  },
  {
    path: DatasetRoute.path,
    element: <CreateDatasetButton/>
  },
  {
    path: UserListRoute.path,
    element: <AddUserButton/>
  },
  {
    path: GroupListRoute.path,
    element: <AddGroupButton/>
  },
  {
    path: ViewListRoute.path,
    element: <AddViewButton/>
  },
  {
    path: ReviewListRoute.path,
    element: <ReviewActionButtons />
  },
  {
    path: '/admin_boundaries/upload_wizard',
    element: <CancelActiveUploadButton />
  }
]
