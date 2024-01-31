import React, {useEffect, useState} from 'react';

import Box from '@mui/material/Box';
import Grid from '@mui/material/Grid';
import Tab from '@mui/material/Tab';
import Tabs from '@mui/material/Tabs';
import Tooltip from '@mui/material/Tooltip';
import Button from '@mui/material/Button';
import Menu from '@mui/material/Menu';
import MenuItem from '@mui/material/MenuItem';
import KeyboardArrowDownIcon from '@mui/icons-material/KeyboardArrowDown';
import SyncProblemIcon from '@mui/icons-material/SyncProblem';
import streamSaver from 'streamsaver';
import ErrorIcon from '@mui/icons-material/Error';
import CircularProgress from '@mui/material/CircularProgress';
import TabPanel, {a11yProps} from '../../components/TabPanel';
import {RootState} from "../../app/store";
import {useAppDispatch, useAppSelector} from "../../app/hooks";
import {updateMenu} from "../../reducers/breadcrumbMenu";
import ViewCreate, {TempQueryCreateInterface} from './ViewCreate';
import {postData} from "../../utils/Requests";
import View, {isReadOnlyView} from "../../models/view";
import DatasetEntities from '../Dataset/DatasetEntities';
import ViewPermission from './ViewPermission';
import ViewSync from './ViewSync';
import '../../styles/ViewDetail.scss';
import {useNavigate, useSearchParams} from "react-router-dom";
import {parseInt} from "lodash";
import TilingConfiguration from '../TilingConfig/TilingConfigRevamp';
import { SyncStatus } from "../../models/syncStatus";
import {updateViewTabStatuses, resetViewTabStatuses} from "../../reducers/viewTabs";
import { StatusAndProgress } from '../../models/syncStatus';
import { fetchSyncStatusAPI } from '../../utils/api/TilingStatus';
import StatusLoadingDialog from '../../components/StatusLoadingDialog';
import ViewDownload from './ViewDownload';

const QUERY_CHECK_URL = '/api/query-view-preview/'
const DOWNLOAD_VIEW_URL = '/api/view-download/'

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
                let _isReadOnly = isReadOnlyView(view)
                if (_isReadOnly) {
                    setTabSelected(1)
                    dispatch(updateMenu({
                        id: `view_edit`,
                        name: `View ${view.name}`
                    }))
                } else {
                    dispatch(updateMenu({
                        id: `view_edit`,
                        name: `Edit ${view.name}`
                    }))
                }
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

    const downloadViewOnClick = (format: string) => {
        setIsDownloading(true)
        let _queryParams = []
        if (previewSession) {
            _queryParams.push(`session=${previewSession}`)
        }
        if (format) {
            _queryParams.push(`format=${format}`) 
        }
        fetch(`${DOWNLOAD_VIEW_URL}${view.id}/?${_queryParams.join('&')}`)
        .then((response) => {
            setIsDownloading(false)
            if (response.status === 200) {
                const readableStream = response.body
                let _filename = response.headers.get('content-disposition').split('filename=')[1].split(';')[0]
                _filename = _filename.replaceAll('"', '')
                const fileStream = streamSaver.createWriteStream(_filename)
                // more optimized
                if (window.WritableStream && readableStream.pipeTo) {
                    return readableStream.pipeTo(fileStream)
                            .then(() => {})
                }
                (window as any).writer = fileStream.getWriter()

                const reader = response.body.getReader()
                const pump = () => reader.read()
                    .then(res => res.done
                    ? (window as any).writer.close()
                    : (window as any).writer.write(res.value).then(pump))
                pump()
            } else if (response.status === 404) {
                alert('Error! The requested file does not exist!')
            } else {
                response.json().then((data) => {
                    let _json = data as {detail?:string}
                    if (_json && _json.detail) {
                        alert(`Failed to download: ${_json.detail}`)
                    } else {
                        alert('Failed to download the requested file!')
                    }
                })                
            }
        })
        .catch((error) => {
            setIsDownloading(false)
            console.log('Failed to download file!', error)
            alert('Failed to download the requested file!')
        })
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
                    <Tab label="Preview" {...a11yProps(1)} disabled={!isQueryValid} />
                    <Tab label="Download" {...a11yProps(2)} disabled={!isQueryValid} />
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