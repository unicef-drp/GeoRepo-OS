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
import {UserDetailRoute, UserProfileRoute} from '../routes';
import UserInterface from '../../models/user';
import UserDetailGeneral from './UserDetailGeneral';
import UserPermission from './UserPermission';
import UserAPIKeys from './UserAPIKeys';

const FETCH_USER_DETAIL_URL = '/api/user/'

export default function UserDetail(props: any) {
    const dispatch = useAppDispatch()
    const navigate = useNavigate()
    const [loading, setLoading] = useState(true)
    const [searchParams, setSearchParams] = useSearchParams()
    const [tabSelected, setTabSelected] = useState(0)
    const [user, setUser] = useState<UserInterface>(null)
    const [isUserProfile, setIsUserProfile] = useState(searchParams.get('id') === null)

    const updateBreadcrumb = (user: UserInterface) => {
      if (!isUserProfile) {
        dispatch(updateMenu({
          id: `user_detail`,
          name: `${user.username} (${user.role})`
        }))
      } else {
        dispatch(updateMenu({
          id: `profile`,
          name: `${user.username} (${user.role})`
        }))
      }
    }

    const fetchUserDetail = (user_id: number) => {
        setLoading(true)
        axios.get(`${FETCH_USER_DETAIL_URL}${user_id}/`).then(
            response => {
              setLoading(false)
              let _user: UserInterface = response.data as UserInterface
              Object.keys(_user).forEach(function(key, index) {
                if (key === 'joined_date' && _user[key]) {
                    _user[key] = moment(_user[key]).local().format('YYYY-MM-DD')
                } else if (key === 'last_login' && _user[key]) {
                    _user[key] = moment(_user[key]).local().format('YYYY-MM-DD HH:mm:ss')
                }
              });
              setUser(_user)
              updateBreadcrumb(_user)
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
        let tab = 0
        if (searchParams.get('tab')) {
            tab = parseInt(searchParams.get('tab'))
            setTabSelected(tab)
        }
        let userId = searchParams.get('id')
        setIsUserProfile(userId === null)
        if (userId && (user == null || (user && user.id != parseInt(userId)))) {
            fetchUserDetail(parseInt(userId))
        } else if (userId === null) {
          // user profile
          fetchUserDetail(parseInt((window as any).user_id))
        }
    }, [searchParams])

    const handleChange = (event: React.SyntheticEvent, newValue: number) => {
      if (!isUserProfile && searchParams.get('id')) {
        navigate(`${UserDetailRoute.path}?id=${searchParams.get('id')}&tab=${newValue}`)
      } else {
        navigate(`${UserProfileRoute.path}?tab=${newValue}`)
      }
    }

    const onUserUpdated = () => {
      let userId = searchParams.get('id')
      if (userId) {
        fetchUserDetail(parseInt(userId))
      } else {
        // user profile
        fetchUserDetail(parseInt((window as any).user_id))
      }
    }

    return (
        <div style={{display:'flex', flex: 1, flexDirection: 'column'}}>
            <Box sx={{ borderBottom: 1, borderColor: 'divider' }}>
                <Tabs value={tabSelected} onChange={handleChange} aria-label="User Tab">
                    <Tab key={'tab-0'} label={'DETAIL'} {...a11yProps(0)} />
                    {/* disable permission tab if it's super user */}
                    <Tab key={'tab-1'} {...a11yProps(1)} disabled={user?.role === 'Admin'}
                        style={{ pointerEvents: "auto" }}
                        label={user?.role === 'Admin' ? 
                        <Tooltip title="Admin role has all permissions">
                            <span>PERMISSION</span>
                        </Tooltip> : 'PERMISSION'}  />
                      <Tab key={'tab-2'} label={'API Key Enrolment'} {...a11yProps(0)} />
                </Tabs>
            </Box>
            { loading && <Skeleton variant="rectangular" height={'100%'} width={'100%'}/> }
            { !loading && (
              <Grid container sx={{ flexGrow: 1, flexDirection: 'column' }}>
                <TabPanel key={0} value={tabSelected} index={0} padding={1}>
                    <UserDetailGeneral isUserProfile={isUserProfile} user={user} onUserUpdated={onUserUpdated} />
                </TabPanel>
                <TabPanel key={1} value={tabSelected} index={1} padding={1}>
                    <UserPermission isUserProfile={isUserProfile} user={user} />
                </TabPanel>
                <TabPanel key={2} value={tabSelected} index={2} padding={1}>
                    <UserAPIKeys user={user} isUserProfile={isUserProfile} />
                </TabPanel>
              </Grid>
            )}
        </div>
    )

}
