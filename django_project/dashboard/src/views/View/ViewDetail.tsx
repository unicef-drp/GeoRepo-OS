import React, {useEffect, useState} from 'react';

import Box from '@mui/material/Box';
import Grid from '@mui/material/Grid';
import Tab from '@mui/material/Tab';
import Tabs from '@mui/material/Tabs';
import Tooltip from '@mui/material/Tooltip';
import Button from '@mui/material/Button';
import SyncProblemIcon from '@mui/icons-material/SyncProblem';
import ErrorIcon from '@mui/icons-material/Error';
import CircularProgress from '@mui/material/CircularProgress';
import TabPanel, {a11yProps} from '../../components/TabPanel';
import {RootState} from "../../app/store";
import {useAppDispatch, useAppSelector} from "../../app/hooks";
import {updateMenu, insertBefore} from "../../reducers/breadcrumbMenu";
import ViewCreate, {TempQueryCreateInterface} from './ViewCreate';
import {postData} from "../../utils/Requests";
import View, {isReadOnlyView} from "../../models/view";
import DatasetEntities from '../Dataset/DatasetEntities';
import ViewPermission from './ViewPermission';
import ViewSync from './ViewSync';
import '../../styles/ViewDetail.scss';
import {useNavigate, useSearchParams} from "react-router-dom";
import {parseInt, toLower} from "lodash";
import TilingConfiguration from '../TilingConfig/TilingConfigRevamp';
import { SyncStatus } from "../../models/syncStatus";
import {updateViewTabStatuses, resetViewTabStatuses} from "../../reducers/viewTabs";
import { StatusAndProgress } from '../../models/syncStatus';
import { fetchSyncStatusAPI } from '../../utils/api/TilingStatus';
import StatusLoadingDialog from '../../components/StatusLoadingDialog';
import ViewDownload from './ViewDownload';

const QUERY_CHECK_URL = '/api/query-view-preview/'

interface ButtonContainerInterface {
    children?: React.ReactNode;
    onClick: () => void;
}

export default function ViewDetail() {
    const dispatch = useAppDispatch()
    const [tabSelected, setTabSelected] = useState(0)
    const [isQueryValid, setIsQueryValid] = useState(false)
    const [previewSession, setPreviewSession] = useState(null)
    const [tempData, setTempData] = useState<TempQueryCreateInterface>(null)
    const [view, setView] = useState<View>(null)
    const [isDownloading, setIsDownloading] = useState(false)
    const [searchParams, setSearchParams] = useSearchParams()
    const navigate = useNavigate()
    const objSyncStatus = useAppSelector((state: RootState) => state.viewTabs.objSyncStatus)
    
    const fetchTilingStatus = () => {
        if (view === null || !view.id) return
        let _object_type = 'datasetview'
        let _object_uuid = view.uuid
        fetchSyncStatusAPI(_object_type, _object_uuid, (response: any, error: any) => {
           if (response) {
                let _simplification: StatusAndProgress = {
                    progress: response['simplification']['progress'],
                    status: response['simplification']['status']
                }
                let _obj_status = response['sync_status']
                dispatch(updateViewTabStatuses({
                    objSyncStatus: _obj_status,
                    simplificationStatus: _simplification
                }))
           }
        })
    }

    useEffect(() => {
        // reset previous state from other view
        dispatch(resetViewTabStatuses())
    }, [])

    useEffect(() => {
        if (view) {
            setPreviewSession(view.preview_session)
            if (view.id) {
                let tab = searchParams.get('tab') ? parseInt(searchParams.get('tab')) : 0
                setTabSelected(tab as unknown as number)
                let _viewName = view.name
                if (view.is_default === 'Yes') {
                    _viewName = _viewName.replaceAll(` - ${view.dataset_name}`, '')
                    // old format
                    _viewName = _viewName.replaceAll(`${view.dataset_name} - `, '')
                }
                let _isReadOnly = isReadOnlyView(view)
                if (_isReadOnly) {
                    // set tab to preview if accessing tab > 2
                    let _tab = tab <= 2 ? tab : 1
                    setTabSelected(_tab)
                    dispatch(updateMenu({
                        id: `view_edit`,
                        name: `View ${_viewName}`
                    }))
                } else {
                    dispatch(updateMenu({
                        id: `view_edit`,
                        name: `Edit ${_viewName}`
                    }))
                }
                let moduleName = toLower(view.module_name.replace(' ', '_'))
                dispatch(insertBefore({
                    'beforeId': 'view_edit',
                    'newMenu': {
                        'id': 'dataset_link',
                        'name': view.dataset_name,
                        'link': `/${moduleName}/dataset_entities?id=${view.dataset}`
                    }
                }))
                fetchTilingStatus()
            }
        }
    }, [view, searchParams])

    const onQueryValidation = (isValid: boolean, query: string) => {
        if (view) {
            // detail page, check if query is changed
            if (view.query_string != query) {
                setIsQueryValid(isValid)
            } else {
                // set query valid if this is from detail
                setIsQueryValid(true)
            }
        } else {
            setIsQueryValid(isValid)
        }
    }

    const handleChange = (event: React.SyntheticEvent, newValue: number) => {
        if (tempData) {
            setTabSelected(0)
            return
        }
        let viewId = searchParams.get('id') ? parseInt(searchParams.get('id')) : 0
        navigate(`/view_edit?id=${viewId}&tab=${newValue}`)
    }

    const onPreviewClicked = (tempData: TempQueryCreateInterface) => {
        let _post_data:any = {
            'query_string': tempData.queryString,
            'dataset': tempData.dataset
        }
        if (previewSession) {
            _post_data['session'] = previewSession
        }
        postData(QUERY_CHECK_URL, _post_data).then(
            response => {
                setTempData(tempData)
                setPreviewSession(response.data['session'])
                setTabSelected(1)
            }
          ).catch(
            error => {
                setTempData(null)
                console.log(error)
            }
          )
    }

    const onViewUpdated = () => {

    }

    const getSyncStatusTab = () => {
        if (objSyncStatus === SyncStatus.Syncing) {
            return <Tab key={5} label="Sync Status"
              icon={<CircularProgress size={18} />}
              iconPosition={'start'}
              {...a11yProps(5)}
              disabled={view === null}
            />
          } else if (objSyncStatus === SyncStatus.Error) {
            return <Tab key={5} label="Sync Status"
              icon={<ErrorIcon color='error' fontSize='small' />}
              iconPosition={'start'}
              {...a11yProps(5)}
              disabled={view === null}
            />
          } else if (objSyncStatus === SyncStatus.OutOfSync) {
            return <Tab key={5} label="Sync Status"
              icon={<SyncProblemIcon color='warning' fontSize='small' />}
              iconPosition={'start'}
              {...a11yProps(5)}
              disabled={view === null}
            />
          }
        return <Tab label="Sync Status" {...a11yProps(4)} disabled={view === null} />
    }

    return (
        <div style={{display:'flex', flex: 1, flexDirection: 'column'}}>
            <StatusLoadingDialog open={isDownloading} title={'Download product data'} description={'Please wait while system is preparing the data...'} />
            <Box display={'flex'} flexDirection={'row'} justifyContent={'space-between'} sx={{ borderBottom: 1, borderColor: 'divider' }}>
                <Tabs className='DatasetTabs' value={tabSelected} onChange={handleChange} aria-label="Configuration Tab">
                    <Tab label={ "Detail" + (tempData != null ? "*" : "") } {...a11yProps(0)} />
                    <Tab label="Preview" {...a11yProps(1)} disabled={view === null} />
                    <Tab label="Download History" {...a11yProps(2)} disabled={view === null} onClick={() => {
                        if (tabSelected !== 2) return;
                        if (searchParams.get('filterSession') || searchParams.get('requestId')) {
                            handleChange(null, 2)
                        }
                    }} />
                    { view && view.permissions && view.permissions.includes('Manage') && (
                        <Tab label="Permission" {...a11yProps(3)} disabled={view === null} />
                    )}
                    { view && view.permissions && view.permissions.includes('Manage') && (
                        <Tab label="Tiling Config" {...a11yProps(4)} disabled={view === null} />
                    )}
                    { view && view.permissions && view.permissions.includes('Manage') && getSyncStatusTab()}
                </Tabs>
                { view && tabSelected === 1 && <Box flexDirection={'column'} justifyContent={'center'} display={'flex'} sx={{marginRight: '20px'}}>
                    <Tooltip title='Download view with filters from the preview'>
                        <Button disabled={!previewSession}
                            id='download-as-button'
                            className={'ThemeButton MuiButton-secondary'}
                            onClick={(event: React.MouseEvent<HTMLButtonElement>) => {
                                let _navigate_to = `/view_edit?id=${view.id}&tab=2&filterSession=${previewSession}`
                                navigate(_navigate_to)
                            }}
                        >
                            Download
                        </Button>
                    </Tooltip>
                </Box>
                }
            </Box>
            <Grid container sx={{ flexGrow: 1, flexDirection: 'column' }}>
                <TabPanel value={tabSelected} index={0}>
                    <ViewCreate onQueryValidation={onQueryValidation}
                     onPreviewClicked={onPreviewClicked} tempData={tempData}
                     onViewLoaded={(view: View) => setView(view)} />
                </TabPanel>
                <TabPanel value={tabSelected} index={1} noPadding>
                    { (tempData && previewSession && tempData.dataset) ? (
                        <Grid container flexDirection={'column'} sx={{height:'100%'}}>
                            <Grid item sx={{display:'flex', flex:1, height:'100%'}}>
                                <DatasetEntities datasetId={tempData.dataset} session={previewSession}
                                    datasetUuid={tempData.datasetUuid}
                                    mapProps={{
                                        'datasetViewUuid': view ? view.uuid : null
                                    }} />
                            </Grid>
                        </Grid>
                    ) : (view && previewSession) ? (
                        <Grid container flexDirection={'column'} sx={{height:'100%'}}>
                            <Grid item sx={{display:'flex', flex:1, height:'100%'}}>
                                <DatasetEntities datasetId={view.dataset} session={previewSession}
                                    datasetUuid={view.dataset_uuid} datasetStyleSourceName={view.dataset_style_source_name}
                                    viewUuid={view.uuid}
                                    mapProps={{
                                        'datasetViewUuid': view.uuid
                                    }} />
                            </Grid>
                        </Grid>
                    ): null
                    }
                </TabPanel>
                <TabPanel value={tabSelected} index={2} noPadding>
                    <ViewDownload view={view} />
                </TabPanel>
                { view && view.permissions && view.permissions.includes('Manage') && (
                    <TabPanel value={tabSelected} index={3} noPadding>
                        <ViewPermission view={view} onViewUpdated={onViewUpdated} />
                    </TabPanel>
                )}
                { view && view.permissions && view.permissions.includes('Manage') && (
                    <TabPanel value={tabSelected} index={4} padding={1}>
                        <TilingConfiguration view={view} isReadOnly={view.is_read_only} onSyncStatusShouldBeUpdated={fetchTilingStatus} />
                    </TabPanel>
                )}
                { view && view.permissions && view.permissions.includes('Manage') && (
                    <TabPanel value={tabSelected} index={5} noPadding>
                        <ViewSync view={view} onSyncStatusShouldBeUpdated={fetchTilingStatus} />
                    </TabPanel>
                )}
            </Grid>
        </div>
    )
}