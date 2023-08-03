import React, {useEffect, useState} from 'react';
import {useSearchParams} from "react-router-dom";
import {useNavigate} from "react-router-dom";
import axios from "axios";
import moment from 'moment';
import Box from '@mui/material/Box';
import Grid from '@mui/material/Grid';
import Tab from '@mui/material/Tab';
import Tabs from '@mui/material/Tabs';
import Tooltip from "@material-ui/core/Tooltip";
import {useAppDispatch} from "../../app/hooks";
import {updateMenu} from "../../reducers/breadcrumbMenu";
import TabPanel, {a11yProps} from '../../components/TabPanel';
import Skeleton from '@mui/material/Skeleton';
import {UserDetailRoute} from '../routes';
import UserInterface from '../../models/user';
import UserCreateGeneral from './UserCreateGeneral';
import UserPermission from './UserPermission';

const FETCH_USER_DETAIL_URL = '/api/user/'

export default function UserCreate(props: any) {
    const dispatch = useAppDispatch()
    const navigate = useNavigate()
    const [loading, setLoading] = useState(false)
    const [searchParams, setSearchParams] = useSearchParams()
    const [tabSelected, setTabSelected] = useState(0)
    const [user, setUser] = useState<UserInterface>(null)


    // const fetchUserDetail = () => {
    //     setLoading(true)
    //     axios.get(`${FETCH_USER_DETAIL_URL}${searchParams.get("id")}/`).then(
    //         response => {
    //           setLoading(false)
    //           let _user: UserInterface = response.data as UserInterface
    //           Object.keys(_user).forEach(function(key, index) {
    //             if (key === 'joined_date' && _user[key]) {
    //                 _user[key] = moment(_user[key]).local().format('YYYY-MM-DD')
    //             } else if (key === 'last_login' && _user[key]) {
    //                 _user[key] = moment(_user[key]).local().format('YYYY-MM-DD HH:mm:ss')
    //             }
    //           });
    //           setUser(_user)
    //           dispatch(updateMenu({
    //             id: `user_detail`,
    //             name: `${_user.username} (${_user.role})`
    //           }))
    //         }
    //       ).catch((error) => {
    //         if (error.response) {
    //           if (error.response.status == 403) {
    //             // TODO: use better way to handle 403
    //             navigate('/invalid_permission')
    //           }
    //         }
    //       })
    // }

    // useEffect(() => {
    //     let tab = 0
    //     if (searchParams.get('tab')) {
    //         tab = parseInt(searchParams.get('tab'))
    //         setTabSelected(tab)
    //     }
    //     let userId = searchParams.get('id')
    //     if (userId && (user == null || (user && user.id != parseInt(userId)))) {
    //         fetchUserDetail()
    //     }
    // }, [searchParams])

    const handleCreate = (newValue: number) => {
        navigate(`${UserDetailRoute.path}?id=1`)
    }

    return (
        <div style={{display:'flex', flex: 1, flexDirection: 'column'}}>
            { loading && <Skeleton variant="rectangular" height={'100%'} width={'100%'}/> }
            { !loading && (
              <Grid container sx={{ flexGrow: 1, flexDirection: 'column' }}>
                <TabPanel key={0} value={tabSelected} index={0} padding={1}>
                    <UserCreateGeneral
                      onUserCreated={handleCreate}
                    />
                </TabPanel>
                <TabPanel key={1} value={tabSelected} index={1} padding={1}>
                    <UserPermission user={user} />
                </TabPanel>
              </Grid>
            )}
        </div>
    )

}
