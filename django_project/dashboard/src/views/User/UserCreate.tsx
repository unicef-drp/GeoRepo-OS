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

    const handleCreate = (userId: number) => {
        navigate(`${UserDetailRoute.path}?id=${userId}`)
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
