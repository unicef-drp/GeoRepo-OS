import React, {useEffect, useState} from 'react';
import {useSearchParams} from "react-router-dom";
import {useNavigate} from "react-router-dom";
import axios from "axios";
import Box from '@mui/material/Box';
import Grid from '@mui/material/Grid';
import Tab from '@mui/material/Tab';
import Tabs from '@mui/material/Tabs';
import {useAppDispatch} from "../../app/hooks";
import {updateMenu} from "../../reducers/breadcrumbMenu";
import TabPanel, {a11yProps} from '../../components/TabPanel';
import Skeleton from '@mui/material/Skeleton';
import {GroupDetailRoute} from '../routes';
import GroupInterface, {createNewGroup} from '../../models/group';
import GroupDetailForm from './GroupDetailForm';
import GroupMembers from './GroupMembers';
import GroupPermission from './GroupPermission';
import '../../styles/Group.scss';

const FETCH_GROUP_DETAIL_URL = '/api/group/'

export default function GroupDetail(props: any) {
    const dispatch = useAppDispatch()
    const navigate = useNavigate()
    const [loading, setLoading] = useState(true)
    const [searchParams, setSearchParams] = useSearchParams()
    const [tabSelected, setTabSelected] = useState(0)
    const [group, setGroup] = useState<GroupInterface>(createNewGroup())
    
    const updateSelectedTab = () => {
        let tab = 0
        if (searchParams.get('tab')) {
            tab = parseInt(searchParams.get('tab'))
            setTabSelected(tab)
        }
    }

    const fetchGroupDetail = () => {
        setLoading(true)
        axios.get(`${FETCH_GROUP_DETAIL_URL}${searchParams.get("id")}/`).then(
            response => {
              setLoading(false)
              let _group: GroupInterface = response.data as GroupInterface
              setGroup(_group)
              dispatch(updateMenu({
                id: `group_detail`,
                name: `${_group.name}`
              }))
              updateSelectedTab()
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
        let groupId = searchParams.get('id') ? parseInt(searchParams.get('id')) : 0
        if (groupId > 0 && (group.id === 0 || (group.id !== groupId))) {
            fetchGroupDetail()
        } else if (groupId === 0) {
            setLoading(false)
            dispatch(updateMenu({
                id: `group_detail`,
                name: `Add New Group`
              }))
              updateSelectedTab()
        } else {
            updateSelectedTab()
        }
    }, [searchParams])

    const handleChange = (event: React.SyntheticEvent, newValue: number) => {
        navigate(`${GroupDetailRoute.path}?id=${searchParams.get('id')}&tab=${newValue}`)
    }

    return (
        <div style={{display:'flex', flex: 1, flexDirection: 'column'}}>
            { loading && <Skeleton variant="rectangular" height={'100%'} width={'100%'}/> }
            { !loading && (
            <Box sx={{ borderBottom: 1, borderColor: 'divider' }}>
                <Tabs value={tabSelected} onChange={handleChange} aria-label="Group Tab">
                    <Tab key={'tab-0'} label={'DETAIL'} {...a11yProps(0)} />
                    { group.id !== 0 &&
                        <Tab key={'tab-1'} label={'MEMBERS'} {...a11yProps(1)} />
                    }
                    { group.id !== 0 &&
                    <Tab key={'tab-2'} label={'PERMISSION'} {...a11yProps(2)} />
                    }
                </Tabs>
            </Box>
            )}
            { !loading && (
              <Grid container sx={{ flexGrow: 1, flexDirection: 'column' }}>
                <TabPanel key={0} value={tabSelected} index={0} padding={1}>
                    <GroupDetailForm group={group} onGroupUpdated={fetchGroupDetail} />
                </TabPanel>
                <TabPanel key={1} value={tabSelected} index={1} padding={1}>
                    <GroupMembers group={group} />
                </TabPanel>
                <TabPanel key={2} value={tabSelected} index={2} padding={1}>
                    <GroupPermission group={group} />
                </TabPanel>
              </Grid>
            )}
        </div>
    )

}
