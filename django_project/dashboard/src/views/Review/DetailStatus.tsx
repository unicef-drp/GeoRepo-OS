import React, {useEffect, useState} from "react";
import {
    Button,
    ButtonGroup,
    Card,
    Grid,
    Skeleton} from "@mui/material";
import axios from "axios";
import { 
    UploadSession,
    APPROVED,
    DISABLED_STATUS_LIST,
    getUploadStatusLabel
} from "../../models/upload";
import {postData} from "../../utils/Requests";
import {useNavigate} from "react-router-dom";
import {DatasetRoute} from "../routes";
import {RootState} from "../../app/store";
import {useAppDispatch, useAppSelector} from "../../app/hooks";
import {setPendingReviews} from "../../reducers/reviewAction";
import AlertMessage from '../../components/AlertMessage';
import AlertDialog from '../../components/AlertDialog';
import StatusLoadingDialog from '../../components/StatusLoadingDialog';

interface ReviewStatusProps {
    data?: UploadSession
}

const APPROVE_URL = '/api/approve-revision/'
const REJECT_URL = '/api/reject-revision/'
const ENTITY_STATUS_UPLOAD_URL = '/api/entity-upload-status-detail/'
const FETCH_PENDING_REVIEWS_URL = '/api/review/batch/uploads/'

export default function ReviewStatus(props: ReviewStatusProps) {
    const [alertOpen, setAlertOpen] = useState<boolean>(false)
    const [isApprove, setIsApprove] = useState<boolean>(true)
    const [alertLoading, setAlertLoading] = useState<boolean>(false)
    const [confirmMessage, setConfirmMessage] = useState<string>('')
    const navigate = useNavigate()
    const dispatch = useAppDispatch()
    const [alertDialogTitle, setAlertDialogTitle] = useState<string>('')
    const [alertDialogDescription, setAlertDialogDescription] = useState<string>('')
    const [statusDialogOpen, setStatusDialogOpen] = useState<boolean>(false)
    const [statusDialogTitle, setStatusDialogTitle] = useState<string>('')
    const [statusDialogDescription, setStatusDialogDescription] = useState<string>('')
    const [approvalFinished, setApprovalFinished] = useState<boolean>(false)
    // check if the review is in pending/processing batch review, if yes, then cannot do approval
    const pendingReviews = useAppSelector((state: RootState) => state.reviewAction.pendingReviews)
    const isReadOnly = Boolean(props.data == null || !props.data.comparisonReady ||
        DISABLED_STATUS_LIST.includes(props.data.uploadStatus) ||
        pendingReviews.includes(parseInt(props.data.entityUploadId)))

    const fetchPendingReviews = () => {
        axios.get(`${FETCH_PENDING_REVIEWS_URL}`).then((response) => {
          if (response.data) {
            dispatch(setPendingReviews(response.data))
          }
        })
      }

    const handleApprove = () => {
        setIsApprove(true)
        setAlertDialogTitle('Approve this data?')
        setAlertDialogDescription('Are you sure you want to approve this data?')
        setAlertOpen(true)
    }

    const handleAlertCancel = () => {
        setAlertOpen(false)
    }

    const handleReject = () => {
        setIsApprove(false)
        setAlertDialogTitle('Reject this data?')
        setAlertDialogDescription('Are you sure you want to reject this data?')
        setAlertOpen(true)
    }

    const redirectAfterApproval = () => {
        setTimeout(() => {
            navigate(DatasetRoute.path)
        }, 3000)
    }

    const alertConfirmed = () => {
        const apiUrl = isApprove ? APPROVE_URL : REJECT_URL;
        const data = {
            entity_upload_id: props.data.entityUploadId
        }
        setAlertLoading(true)
        postData(`${apiUrl}${props.data.datasetUuid}/`, data).then(
            response => {
                // if approve, then trigger interval check for upload_status
                if (isApprove) {
                    setConfirmMessage('')
                    setApprovalFinished(false)
                    setStatusDialogOpen(true)
                    setStatusDialogTitle('Approving the upload')
                    setStatusDialogDescription('Please wait while background task is in progress...')
                } else {
                    setConfirmMessage('Successfully ' + ( isApprove ? 'approving' : 'rejecting' ) + '  this data, redirecting...')
                    redirectAfterApproval()
                }
            }
          ).catch(error => {
                setAlertLoading(false)
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

    useEffect(() => {
        fetchPendingReviews()
    }, [])

    useEffect(() => {
        if (!approvalFinished && statusDialogOpen) {
            const interval = setInterval(() => {
                fetchEntityUploadStatus()
            }, 2000);
            return () => clearInterval(interval)
        }
    }, [approvalFinished, statusDialogOpen])

    const fetchEntityUploadStatus = () => {
        // triggered when approving the review
        // once the status is approved, then show message and redirect user
        axios.get(ENTITY_STATUS_UPLOAD_URL + props.data.entityUploadId).then(
            response => {
                if (response.data) {
                    if (response.data.upload_status === APPROVED) {
                        setApprovalFinished(true)
                        setStatusDialogDescription('Successfully approving this data, redirecting...')
                        redirectAfterApproval()
                    }
                }
        }).catch(error => {
            console.log(error)
            if (error.response) {
                if (error.response.status == 403) {
                    // TODO: use better way to handle 403
                    navigate('/invalid_permission')
                }
            }
        })
    }

    return (
        <Card className='review-status'>
            <AlertMessage message={confirmMessage} onClose={() => setConfirmMessage('')} />
            <AlertDialog open={alertOpen} alertClosed={handleAlertCancel}
                         alertConfirmed={alertConfirmed}
                         alertLoading={alertLoading}
                         alertDialogTitle={alertDialogTitle}
                         alertDialogDescription={alertDialogDescription} />
            <StatusLoadingDialog open={statusDialogOpen} title={statusDialogTitle} description={statusDialogDescription} />
            <Grid container rowSpacing={{ xs: 1 }} lineHeight={1.75}>
                <Grid item xs={4} sm={2} className='review-status-item'>
                    { props.data ? props.data.name : <Skeleton variant="rectangular" width={100}/> }
                </Grid>
                <Grid item xs={4} sm={2} className='review-status-item'>
                    { props.data ? props.data.created_at : <Skeleton variant="rectangular" width={100}/> }
                </Grid>
                <Grid item xs={4} sm={2} className='review-status-item'>
                    { props.data ? props.data.created_by : <Skeleton variant="rectangular" width={100}/> }
                </Grid>
                <Grid item xs={6} sm={2} className='review-status-item'>
                    { props.data ? getUploadStatusLabel(props.data.uploadStatus) : <Skeleton variant="rectangular" width={100}/> }
                </Grid>
                <Grid item xs={6} sm={4} className='review-status-item'>
                    <ButtonGroup
                      disableElevation
                      variant="contained"
                    >
                        <Button disabled={isReadOnly}
                                color={'warning'}
                                onClick={handleReject}
                                title={isReadOnly ? 'The data has been approved' : 'Reject this data'}>
                            Reject
                        </Button>
                        <Button disabled={isReadOnly}
                                onClick={handleApprove}
                                title={isReadOnly ? 'The data has been approved' : 'Approve this data'}>
                            Approve
                        </Button>
                    </ButtonGroup>
                </Grid>
            </Grid>
        </Card>
    )
}
