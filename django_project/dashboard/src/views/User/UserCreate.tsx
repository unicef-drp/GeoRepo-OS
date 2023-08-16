import React, {useState} from 'react';
import {useSearchParams} from "react-router-dom";
import {useNavigate} from "react-router-dom";
import Grid from '@mui/material/Grid';
import {useAppDispatch} from "../../app/hooks";
import TabPanel from '../../components/TabPanel';
import Skeleton from '@mui/material/Skeleton';
import {UserDetailRoute} from '../routes';
import UserInterface from '../../models/user';
import UserCreateGeneral from './UserCreateGeneral';
import UserPermission from './UserPermission';


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
