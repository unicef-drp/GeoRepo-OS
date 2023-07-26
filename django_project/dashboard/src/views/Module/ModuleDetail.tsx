import React, {useEffect, useState} from 'react';
import {useNavigate, useSearchParams} from "react-router-dom";
import Skeleton from '@mui/material/Skeleton';
import Box from '@mui/material/Box';
import Grid from '@mui/material/Grid';
import Tab from '@mui/material/Tab';
import Tabs from '@mui/material/Tabs';
import TabPanel, {a11yProps} from '../../components/TabPanel';
import {fetchData} from "../../utils/Requests";
import {useAppDispatch} from "../../app/hooks";
import {updateMenu} from "../../reducers/breadcrumbMenu";
import {ModuleDetailRoute} from '../routes';
import ModuleInterface from '../../models/module';
import PermissionDetail from '../Permissions/PermissionDetail';
import ModuleDetailGeneral from './ModuleDetailGeneral';

const MODULE_LIST_URL = '/api/module-list/'

export default function ModuleDetail(props: any) {
    const dispatch = useAppDispatch()
    const [loading, setLoading] = useState(true)
    const [searchParams, setSearchParams] = useSearchParams()
    const [moduleUUID, setModuleUUID] = useState('')
    const [tabSelected, setTabSelected] = useState(0)
    const [module, setModule] = useState<ModuleInterface>(null)
    const navigate = useNavigate()

    const fetchModuleDetail = () => {
        setLoading(true)
        fetchData(MODULE_LIST_URL).then(
            response => {
                setLoading(false)
                let _found = false
                for (let module of response.data) {
                    if (module['uuid'] === moduleUUID) {
                        dispatch(updateMenu({
                            id: 'module_detail',
                            name: module['name']
                          }))
                        setModule(module)
                        _found = true
                        break
                    }
                }
                if (!_found) {
                    alert('Module not found!')
                }
            }
        ).catch(error => {
            setLoading(false)
          if (error.response) {
            if (error.response.status == 403) {
              // TODO: use better way to handle 403
              navigate('/invalid_permission')
            }
          }
        })
    }

    useEffect(() => {
        if (moduleUUID) {
            fetchModuleDetail()
        }
    }, [moduleUUID])

    useEffect(() => {
        let tab = 0
        if (searchParams.get('tab')) {
            tab = parseInt(searchParams.get('tab'))
            setTabSelected(tab)
        }
        let uuid = searchParams.get('uuid')
        if (uuid && (module == null || (module && module.uuid != uuid))) {
            setModuleUUID(uuid)
        }
    }, [searchParams])

    const handleChange = (event: React.SyntheticEvent, newValue: number) => {
        navigate(`${ModuleDetailRoute.path}?uuid=${searchParams.get('uuid')}&tab=${newValue}`)
    }

    return (
        <div style={{display:'flex', flex: 1, flexDirection: 'column'}}>
            <Box sx={{ borderBottom: 1, borderColor: 'divider' }}>
                <Tabs value={tabSelected} onChange={handleChange} aria-label="User Tab">
                    <Tab key={'tab-0'} label={'DETAIL'} {...a11yProps(0)} />
                    {/* disable permission tab if it's super user */}
                    <Tab key={'tab-1'} {...a11yProps(1)} disabled={loading}
                        label='PERMISSION'  />
                </Tabs>
            </Box>
            { (loading || moduleUUID === null || moduleUUID === '') && <Skeleton variant="rectangular" height={'100%'} width={'100%'}/> }
            { !loading && moduleUUID && (
              <Grid container sx={{ flexGrow: 1, flexDirection: 'column' }}>
                <TabPanel key={0} value={tabSelected} index={0} padding={1}>
                    <ModuleDetailGeneral module={module} onModuleUpdated={fetchModuleDetail} />
                </TabPanel>
                <TabPanel key={1} value={tabSelected} index={1} padding={1}>
                    <PermissionDetail objectType={'module'} objectUuid={moduleUUID} />
                </TabPanel>
              </Grid>
            )}
        </div>
    )
}

