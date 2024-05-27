import React, {useEffect, useState, useRef} from "react";
import {
    Alert,
    Snackbar,
    AlertColor,
    Slide,
    Typography,
    Link
} from "@mui/material";
import axios from "axios";
import {useNavigate} from "react-router-dom";
import {ReviewListRoute, UploadSessionListRoute} from "../views/routes";
import {useAppDispatch, useAppSelector} from "../app/hooks";
import {
    currentInterval,
    setPollInterval,
    FETCH_INTERVAL_NORMAL
} from "../reducers/notificationPoll";
import {
    setMaintenanceItem,
    removeMaintenanceItem
} from "../reducers/maintenanceItem";
import {setModule} from "../reducers/module";
import {modules} from "../modules";

const NOTIFICATION_LIST_URL = '/api/notification/list/'

interface NotificationInterface {
    id: number,
    type: string,
    message: string,
    recipient: number,
    payload: { [key: string]: string },
    created_at: Date
}

interface NotificationItemInterface {
    data: NotificationInterface,
    handleClose: (id: number, reason?: string) => void,
    open: boolean,
    handleClick?: (id: number) => void
}

function TransitionLeft(props: any) {
    return <Slide {...props} direction="right" />
}

function NotificationItem(props: NotificationItemInterface) {
    const severity: AlertColor = (props.data.payload?.severity ? props.data.payload?.severity :
                                    'success') as AlertColor
    return (
        <Snackbar open={props.open} onClose={(e, reason) => props.handleClose(props.data.id, reason)}
            TransitionComponent={TransitionLeft} autoHideDuration={60000}>
            <Alert variant="filled"
                onClose={() => props.handleClose(props.data.id)} severity={severity} sx={{ width: '100%' }}>
                <Typography onClick={() => props.handleClick?props.handleClick(props.data.id):null}
                    style={{cursor: 'pointer'}}>
                    {props.data.message}
                </Typography>
            </Alert>
        </Snackbar>
        )
}


export default function Notification() {
    const [notifications, setNotifications] = useState<NotificationInterface[]>([])
    const [isNotificationOpen, setIsNotificationOpen] = useState(false)
    const pollInterval = useAppSelector(currentInterval)
    const intervalRef = useRef<ReturnType<typeof setInterval>>(null)
    const navigate = useNavigate()
    const dispatch = useAppDispatch()
    
    useEffect(() => {
        if (intervalRef.current) {
            clearInterval(intervalRef.current)
        }
        intervalRef.current = getInterval()
        return () => {
            clearInterval(intervalRef.current)
            intervalRef.current = null
        }
    }, [pollInterval])

    const getInterval = () => {
        fetchNotifications()
        return setInterval(() => {
            fetchNotifications()
        }, pollInterval * 1000)
    }

    const fetchNotifications = () => {
        // fetch notification list
        axios.get(NOTIFICATION_LIST_URL).then((response) => {
            if (response.data) {
                if (response.data.notifications && response.data.notifications.length) {
                    setNotifications([...notifications, ...response.data.notifications])
                    setIsNotificationOpen(true)
                    dispatch(setPollInterval(FETCH_INTERVAL_NORMAL))
                }
                if (response.data.has_maintenance) {
                    dispatch(setMaintenanceItem({
                        hasMaintenance: response.data.has_maintenance,
                        maintenanceMessage: response.data.maintenance.message,
                        maintenanceId: response.data.maintenance.id
                    }))
                } else {
                    dispatch(removeMaintenanceItem(false))
                }
            }
        }).catch(error => {
            console.log(error)
        })
    }

    const handleAlertOnClose = (id: number, reason?: string) => {
        if (reason === "clickaway")
            return
        const filtered = notifications.filter((item) => item.id !== id)
        setIsNotificationOpen(filtered.length > 0)
        setNotifications(filtered)
    }

    const handleAlertOnClick = (id: number) => {
        const filtered = notifications.filter((item) => item.id === id)
        if (!filtered)
            return
        const notification = filtered[0]
        // handle based on notification type
        switch (notification.type) {
            case 'LAYER_VALIDATION':
            case 'PARENT_MATCHING':
                // redirect to upload wizard
                if (!('session' in notification.payload && 'dataset' in notification.payload)) {
                    navigate(UploadSessionListRoute.path)
                    return
                }
                    
                let moduleName = notification.payload.module
                if (!moduleName) {
                    moduleName = modules[0]
                }
                dispatch(setModule(moduleName))
                let _url = `/${moduleName}/upload_wizard/?session=${notification.payload.session}&`+
                `dataset=${notification.payload.dataset}&step=${notification.payload.step}`
                if (notification.type === 'LAYER_VALIDATION') {
                    _url = _url + '&filter_status=All'
                }
                navigate(_url)
                break;
            case 'BOUNDARY_MATCHING':
                // redirect to review detail page
                if ('review_id' in notification.payload)
                    navigate(ReviewListRoute.path + `?upload=${notification.payload.review_id}`)
                else
                    navigate(ReviewListRoute.path)
                break;
            case 'BATCH_REVIEW':
                navigate(ReviewListRoute.path)
                break;
            case 'BATCH_ENTITY_EDIT':
                let moduleName2 = notification.payload.module
                dispatch(setModule(moduleName2))
                let _url2 = `/${moduleName2}/edit_entity/wizard/?session=${notification.payload.session}&`+
                `dataset=${notification.payload.dataset}&step=${notification.payload.step}`
                navigate(_url2)
                break;
            case 'DATASET_VIEW_EXPORTER':
                let _viewId = notification.payload.view_id
                let _reqId = notification.payload.request_id
                let _url3 = `/view_edit?id=${_viewId}&tab=2&requestId=${_reqId}`
                navigate(_url3)
                break;
            default:
                break;
        }
        handleAlertOnClose(id)
    }
    // snackbar can only show 1 item at item to follow material design guide
    return (<div>
        {notifications.map((notification, index) => {
            if (index > 0)
                return
            return (<NotificationItem key={notification.id} data={notification} open={true} 
                handleClose={handleAlertOnClose} handleClick={handleAlertOnClick} />)
        })}
    </div>)
}