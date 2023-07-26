import React, {useEffect, useState} from 'react';
import {useNavigate} from "react-router-dom";
import axios from "axios";
import Skeleton from '@mui/material/Skeleton';
import Grid from '@mui/material/Grid';
import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';
import Button from '@mui/material/Button';
import Loading from "../../components/Loading";
import FormControl from '@mui/material/FormControl';
import TextField from '@mui/material/TextField';
import Modal from '@mui/material/Modal';
import {useAppDispatch} from "../../app/hooks";
import {updateMenu} from "../../reducers/breadcrumbMenu";
import AlertMessage from '../../components/AlertMessage';
import {postData} from "../../utils/Requests";
import List from "../../components/List";
import { AccessRequestDetailInterface } from '../../models/access';
import '../../styles/AccessRequest.scss';


const ACCESS_REQUEST_URL = '/api/access/request/permission/submit/'

export default function SubmitAccessRequest() {
    const dispatch = useAppDispatch()
    const navigate = useNavigate()
    const [loading, setLoading] = useState(true)
    const [hasPendingRequest, setHasPendingRequest] = useState(false)
    const [data, setData] = useState<AccessRequestDetailInterface>(null)
    const [previousRequests, setPreviousRequests] = useState<AccessRequestDetailInterface[]>([])
    const [alertMessage, setAlertMessage] = useState<string>('')
    const [requestDescription, setRequestDescription] = useState<string>('')
    const [userEmail, setUserEmail] = useState<string>('')
    const [requiresEmail, setRequiresEmail] = useState<boolean>(false)
    const [showPrevRequestsModal, setShowPrevRequestsModal] = useState<boolean>(false)

    const checkPendingRequest = () => {
        setLoading(true)
        axios.get(`${ACCESS_REQUEST_URL}`).then(
            response => {
              setLoading(false)
              if (response.data['request']) {
                let _data = response.data['request'] as AccessRequestDetailInterface
                setData(_data)
              } else {
                setData(null)
              }
              setHasPendingRequest(response.data['has_pending_request'])
              if (response.data['has_pending_request']) {
                dispatch(updateMenu({
                    id: `access_request_submit`,
                    name: `View Pending Access Request`
                }))
              } else {
                dispatch(updateMenu({
                    id: `access_request_submit`,
                    name: `Submit New Access Request`
                }))
              }
              setPreviousRequests(response.data['previous_requests'] as AccessRequestDetailInterface[])
              setUserEmail(response.data['user_email'])
              if (response.data['user_email']) {
                setRequiresEmail(false)
              } else {
                setRequiresEmail(true)
              }
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

    const submitAccessRequest = (description: string, userEmail: string) => {
        if (description === null || description.trim().length === 0) {
            alert('Please provide a brief description of your request!')
            return;
        }
        if (requiresEmail && (userEmail === null || userEmail.trim().length === 0)) {
            alert('Please provide your email address!')
            return;
        }
        setLoading(true)
        let _data = {
            'description': description.trim(),
            'user_email': userEmail.trim()
        }
        postData(`${ACCESS_REQUEST_URL}`, _data).then(
            response => {
                setLoading(false)
                setAlertMessage('Your request has been successfully submitted!')
                checkPendingRequest()
            }
          ).catch(error => {
            setLoading(false)
            console.log('error ', error)
            if (error.response) {
                if (error.response.status == 403) {
                  // TODO: use better way to handle 403
                  navigate('/invalid_permission')
                } else if (error.response.data && error.response.data['detail']) {
                  alert(`Error! ${error.response.data['detail']}`)
                } else {
                  alert(`Error submitting the request!`)
                }
            } else {
                alert(`Error submitting the request!`)
            }
          })
    }

    useEffect(() => {
        checkPendingRequest()
    },[])

    return (
        <div className="AdminContentMain">
            <Grid container sx={{ flexGrow: 1, flexDirection: 'column', textAlign: 'left' }}>
                <AlertMessage message={alertMessage} onClose={() => {
                    setAlertMessage('')
                }} />
                { loading && <div className={"loading-container"}><Loading/></div> }
                { !loading && !hasPendingRequest && (
                    <Grid item>
                        <Grid container flexDirection={'column'} sx={{width: '50%', paddingTop: '20px'}}>
                            <FormControl className='FormContent'>
                                { previousRequests.length > 0 ? (
                                    <Grid container sx={{paddingBottom: '10px'}}>
                                        <Grid item>
                                            <Button
                                                variant={"contained"}
                                                disabled={loading}
                                                onClick={() => setShowPrevRequestsModal(true)}>
                                                    Show Previous Requests
                                            </Button>
                                        </Grid>
                                    </Grid>
                                ) : null }
                                <Grid container flexDirection={'column'} columnSpacing={2} rowSpacing={2}>
                                    <Grid className={'form-label'} item md={12} xl={12} xs={12}>
                                        <Typography variant={'subtitle1'}>Brief description of your request</Typography>
                                    </Grid>
                                    <Grid item md={12} xs={12} sx={{ display: 'flex' }}>
                                        <TextField
                                            disabled={loading}
                                            id="input_description"
                                            hiddenLabel={true}
                                            type={"text"}
                                            onChange={val => setRequestDescription(val.target.value)}
                                            value={requestDescription}
                                            multiline
                                            rows={4}
                                            inputProps={{
                                                maxLength: 512
                                            }}
                                            sx={{ width: '100%' }}
                                        />
                                    </Grid>
                                    { requiresEmail && (
                                        <Grid className={'form-label'} item md={4} xl={4} xs={12}>
                                            <Typography variant={'subtitle1'}>Confirm your email address</Typography>
                                        </Grid>
                                    )}
                                    { requiresEmail && (
                                        <Grid item md={8} xs={12} sx={{ display: 'flex' }}>
                                            <TextField
                                                disabled={loading}
                                                id="input_email_address"
                                                hiddenLabel={true}
                                                type={"email"}
                                                onChange={val => setUserEmail(val.target.value)}
                                                value={userEmail}
                                                inputProps={{
                                                    maxLength: 254
                                                }}
                                                sx={{ width: '100%' }}
                                            />
                                        </Grid>
                                    )}
                                </Grid>
                                <Grid container columnSpacing={2} rowSpacing={2} sx={{paddingTop: '1em'}} flexDirection={'row'} justifyContent={'flex-end'}>
                                    <Grid item>
                                        <div className='button-container'>
                                            <Button
                                                variant={"contained"}
                                                disabled={loading}
                                                onClick={() => submitAccessRequest(requestDescription, userEmail)}>
                                                <span style={{ display: 'flex' }}>
                                                { loading ? <Loading size={20} style={{ marginRight: 10 }}/> : ''} { "Submit" }</span>
                                            </Button>
                                        </div>
                                    </Grid>
                                </Grid>
                            </FormControl>
                        </Grid>
                    </Grid>
                )}
                { !loading && hasPendingRequest && (
                    <Grid item>
                        <Grid container flexDirection={'column'} sx={{paddingTop: '20px'}}>
                            <Grid item>
                                { previousRequests.length > 0 ? (
                                    <Grid container sx={{paddingBottom: '10px'}}>
                                        <Grid item>
                                            <Button
                                                variant={"contained"}
                                                disabled={loading}
                                                onClick={() => setShowPrevRequestsModal(true)}>
                                                    Show Previous Requests
                                            </Button>
                                        </Grid>
                                    </Grid>
                                ) : null }
                                <Grid container columnSpacing={2} rowSpacing={2} sx={{width: '80%', textAlign: 'left'}}>
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
                                    <Grid item md={6} xl={6} xs={12}>
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
                        </Grid>
                    </Grid>
                )}

                <Modal open={showPrevRequestsModal} onClose={() => setShowPrevRequestsModal(false)}>
                    <Box className="AccessRequestModal">
                        <List
                            pageName={''}
                            listUrl={''}
                            initData={previousRequests}
                            selectionChanged={null}
                            excludedColumns={['type', 'uuid', 'requester_first_name', 'requester_last_name', 'requester_email', 'description', 'request_by_id', 'approved_by_id']}
                        />
                    </Box>
                </Modal>
            </Grid>
        </div>
    )
}

