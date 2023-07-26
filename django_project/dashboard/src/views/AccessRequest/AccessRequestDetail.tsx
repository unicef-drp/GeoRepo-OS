import React, {useEffect, useState} from 'react';
import {useSearchParams} from "react-router-dom";
import {useNavigate} from "react-router-dom";
import axios from "axios";
import Skeleton from '@mui/material/Skeleton';
import Grid from '@mui/material/Grid';
import Typography from '@mui/material/Typography';
import Button from '@mui/material/Button';
import Divider from '@mui/material/Divider';
import Loading from "../../components/Loading";
import {useAppDispatch} from "../../app/hooks";
import {updateMenu} from "../../reducers/breadcrumbMenu";
import { AccessRequestDetailInterface } from '../../models/access';
import FormDialog from '../../components/FormDialog';
import AlertMessage from '../../components/AlertMessage';
import {postData} from "../../utils/Requests";
import {UserDetailRoute} from '../routes';


const FETCH_ACCESS_REQUEST_DETAIL = '/api/access/request/detail/'

interface RequestFormInterface {
  data: AccessRequestDetailInterface;
  onActionSubmitted: (isApprove: boolean) => void;
}

const getName = (firstName: string, lastName: string): string => {
  if (!firstName) {
    return '-'
  }
  if (firstName && lastName) {
    return `${firstName} ${lastName}`
  }
  return `${firstName}`
}

function UserRequestForm(props: RequestFormInterface) {
  const { data, onActionSubmitted } = props
  const navigate = useNavigate()
  const [loading, setLoading] = useState(false)
  const [isApprove, setIsApprove] = useState(false)
  const [confirmDialogOpen, setConfirmDialogOpen] = useState(false)
  const [dialogTitle, setDialogTitle] = useState('')
  const [dialogContent, setDialogContent] = useState('')

  const approveRequest = () => {
    setIsApprove(true)
    setDialogTitle('Approve this request')
    if (data.type === 'NEW_USER') {
      setDialogContent('Are you sure you want to approve this request? A new user will be created when you approve this request.')
    } else {
      setDialogContent('Are you sure you want to approve this request?')
    }
    
    setConfirmDialogOpen(true)
  }

  const rejectRequest = () => {
    setIsApprove(false)
    setDialogTitle('Reject this request')
    setDialogContent('Are you sure you want to reject this request?')
    setConfirmDialogOpen(true)    
  }

  const onConfirmationClosed = () => {
    setConfirmDialogOpen(false)
  }

  const onConfirmedDialog = (textValue: string)  => {
    let _data = {
      'is_approve': isApprove,
      'remarks': textValue
    }
    setLoading(true)
    postData(`${FETCH_ACCESS_REQUEST_DETAIL}${data.id}/`, _data).then(
      response => {
          setLoading(false)
          onConfirmationClosed()
          onActionSubmitted(isApprove)
      }
    ).catch(error => {
      setLoading(false)
      onConfirmationClosed()
      console.log('error ', error)
      if (error.response) {
          if (error.response.status == 403) {
            // TODO: use better way to handle 403
            navigate('/invalid_permission')
          } else if (error.response.data && error.response.data['detail']) {
            alert(`Error! ${error.response.data['detail']}`)
          } else {
            alert(`Error ${isApprove ? 'approving' : 'rejecting'} the request!`)
          }
      } else {
          alert(`Error ${isApprove ? 'approving' : 'rejecting'} the request!`)
      }
    })
  }

  return (
      <Grid container flexDirection={'column'} rowSpacing={2} sx={{padding: '20px'}}>
        <Grid item>
          <Grid container columnSpacing={2} rowSpacing={2} sx={{width: '80%', textAlign: 'left'}}>
            <Grid item md={6} xl={6} xs={12}>
              <Grid container columnSpacing={2} rowSpacing={2}>
                <Grid className={'form-label'} item md={4} xl={4} xs={12}>
                    <Typography variant={'subtitle1'}>Name</Typography>
                </Grid>
                <Grid item md={8} xs={12} sx={{ display: 'flex' }}>
                    <Typography variant={'subtitle1'}>: {getName(data.requester_first_name, data.requester_last_name)}</Typography>
                </Grid>
                <Grid className={'form-label'} item md={4} xl={4} xs={12}>
                    <Typography variant={'subtitle1'}>Email</Typography>
                </Grid>
                <Grid item md={8} xs={12} sx={{ display: 'flex' }}>
                    <Typography variant={'subtitle1'}>: {`${data.requester_email}`}</Typography>
                </Grid>
              </Grid>
            </Grid>
            <Grid item md={6} xl={6} xs={12}>
              <Grid container columnSpacing={2} rowSpacing={2}>
                <Grid className={'form-label'} item md={4} xl={4} xs={12}>
                    <Typography variant={'subtitle1'}>Submitted Date</Typography>
                </Grid>
                <Grid item md={8} xs={12} sx={{ display: 'flex' }}>
                    <Typography variant={'subtitle1'}>: {`${new Date(data.submitted_on).toDateString()}`}</Typography>
                </Grid>
                <Grid className={'form-label'} item md={4} xl={4} xs={12}>
                  <Typography variant={'subtitle1'}>Status</Typography>
                </Grid>
                <Grid item md={8} xs={12} sx={{ display: 'flex' }}>
                    <Typography variant={'subtitle1'}>: {`${data.status}`}</Typography>                
                </Grid>
              </Grid>
            </Grid>
            <Grid item md={12} xl={12} xs={12}>
              <Grid container columnSpacing={2} rowSpacing={2}>
                <Grid className={'form-label'} item md={2} xl={2} xs={12}>
                    <Typography variant={'subtitle1'}>Description</Typography>
                </Grid>
                <Grid item md={8} xl={8} xs={12} sx={{ display: 'flex' }}>
                    <Typography variant={'subtitle1'}>:&nbsp;</Typography>
                    <Typography variant={'subtitle1'}><p style={{margin:0}}>{`${data.description}`}</p></Typography>                
                </Grid>
              </Grid>
            </Grid>
          </Grid>
        </Grid>
        { data.status !== 'PENDING' && (
          <Grid item>
            <Grid container flexDirection={'column'} rowSpacing={2}>
              <Grid item>
                <Divider variant="middle" sx={{marginTop: '20px', marginLeft: 0, marginRight: 0}} />
              </Grid>
              <Grid item>
                <Grid container columnSpacing={2} rowSpacing={2} sx={{width: '80%', textAlign: 'left'}}>
                  <Grid item md={6} xl={6} xs={12}>
                    <Grid container columnSpacing={2} rowSpacing={2}>
                      <Grid className={'form-label'} item md={4} xl={4} xs={12}>
                      <Typography variant={'subtitle1'}>{ data.status === 'APPROVED' ? 'Approved by': 'Rejected by'}</Typography>
                    </Grid>
                    <Grid item md={8} xs={12} sx={{ display: 'flex' }}>
                        <Typography variant={'subtitle1'}>: {`${data.approval_by}`}</Typography>
                    </Grid>
                    <Grid className={'form-label'} item md={4} xl={4} xs={12}>
                        <Typography variant={'subtitle1'}>{ data.status === 'APPROVED' ? 'Approved Date': 'Rejected Date'}</Typography>
                    </Grid>
                    <Grid item md={8} xs={12} sx={{ display: 'flex' }}>
                        <Typography variant={'subtitle1'}>: {`${new Date(data.approved_date).toDateString()}`}</Typography>
                    </Grid>
                    { data.approver_notes && (
                      <Grid className={'form-label'} item md={4} xl={4} xs={12}>
                          <Typography variant={'subtitle1'}>{ 'Remarks'}</Typography>
                      </Grid>
                    )}
                    { data.approver_notes && (
                      <Grid item md={8} xs={12} sx={{ display: 'flex' }}>
                        <Typography variant={'subtitle1'}>:&nbsp;</Typography>
                        <Typography variant={'subtitle1'}><p style={{margin:0}}>{`${data.approver_notes}`}</p></Typography>                
                      </Grid>
                    )}
                    </Grid>
                  </Grid>
                </Grid>
              </Grid>
            </Grid>
          </Grid>
        )}
        { data.status === 'PENDING' && (
          <Grid item sx={{textAlign: 'left', marginTop: '20px'}}>
            <div className='button-container'>
                <Button
                    variant={"contained"}
                    disabled={loading}
                    onClick={approveRequest}>
                    <span style={{ display: 'flex' }}>
                    { loading ? <Loading size={20} style={{ marginRight: 10 }}/> : ''} { "Approve" }</span>
                </Button>
                <Button
                    variant={"contained"}
                    color='error'
                    disabled={loading}
                    onClick={rejectRequest}
                    sx={{marginLeft: '20px'}}>
                    <span style={{ display: 'flex' }}>
                    { loading ? <Loading size={20} style={{ marginRight: 10 }}/> : ''} { "Reject" }</span>
                </Button>
            </div>
          </Grid>
        )}
        { data.status === 'APPROVED' && (
          <Grid item sx={{textAlign: 'left'}}>
            <Button
                variant={"contained"}
                onClick={() => navigate(`${UserDetailRoute.path}?id=${data.request_by_id}&tab=1`)}>
                  Manage User Permission
            </Button>
          </Grid>
        )}
        <Grid item>
          <FormDialog open={confirmDialogOpen} dialogTitle={dialogTitle} dialogContent={dialogContent}
            inputLabel='Remarks (Optional)' onSubmitted={onConfirmedDialog} onClosed={onConfirmationClosed} />
        </Grid>
      </Grid>
  )
}

export default function AccessRequestDetail() {
  const dispatch = useAppDispatch()
  const navigate = useNavigate()
  const [loading, setLoading] = useState(true)
  const [searchParams, setSearchParams] = useSearchParams()
  const [data, setData] = useState<AccessRequestDetailInterface>(null)
  const [alertMessage, setAlertMessage] = useState<string>('')

  const fetchAccessRequestDetail = () => {
    setLoading(true)
    let _request_id = searchParams.get('id')
    axios.get(`${FETCH_ACCESS_REQUEST_DETAIL}${_request_id}/`).then(
        response => {
          setLoading(false)
          let _data = response.data as AccessRequestDetailInterface
          let _page_title = _data.requester_email
          if (_data.requester_first_name) {
            _page_title = `${_data.requester_first_name}${_data.requester_last_name?' '+_data.requester_last_name:''}`
          }
          if (_data.type === 'NEW_USER') {
            _page_title = 'New User Request: ' + _page_title
          } else {
            _page_title = _page_title + ' Permission Request'
          }
          setData(_data)
          dispatch(updateMenu({
            id: `access_request_detail`,
            name: `${_page_title}`
          }))
        }
      ).catch((error) => {
        if (error.response) {
          if (error.response.status == 403) {
            // TODO: use better way to handle 403
            navigate('/invalid_permission')
          }
        }
      })
  }

  useEffect(() => {
      fetchAccessRequestDetail()
  }, [searchParams])

  const onActionSubmitted = (isApprove: boolean) => {
    fetchAccessRequestDetail()
    setAlertMessage(`Successfully ${isApprove ? 'approving' : 'rejecting'} this request!`)
  }

  return (
      <div style={{display:'flex', flex: 1, flexDirection: 'column'}}>
        <AlertMessage message={alertMessage} onClose={() => {
              setAlertMessage('')
          }} />
        { loading && <Skeleton variant="rectangular" height={'100%'} width={'100%'}/> }
        { !loading &&  <UserRequestForm data={data} onActionSubmitted={onActionSubmitted} /> }
      </div>
  )
}
