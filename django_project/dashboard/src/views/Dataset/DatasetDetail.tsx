import React, {useEffect, useState} from 'react';
import {useSearchParams} from "react-router-dom";
import {useNavigate} from "react-router-dom";
import axios from "axios";
import {RootState} from "../../app/store";
import {useAppDispatch, useAppSelector} from "../../app/hooks";
import {setModule} from "../../reducers/module";
import {updateMenu, currentDataset, changeCurrentDataset} from "../../reducers/breadcrumbMenu";
import Box from '@mui/material/Box';
import Grid from '@mui/material/Grid';
import Tab from '@mui/material/Tab';
import Tabs from '@mui/material/Tabs';
import CircularProgress from '@mui/material/CircularProgress';
import ErrorIcon from '@mui/icons-material/Error';
import TabPanel, {a11yProps} from '../../components/TabPanel';
import Skeleton from '@mui/material/Skeleton';
import Dataset from '../../models/dataset';
import { DatasetDetailItemInterface, DatasetTabElementInterface } from '../../models/dataset';
import { SyncStatus } from "../../models/syncStatus";
import { StatusAndProgress } from '../../models/syncStatus';
import { fetchTilingStatusAPI } from '../../utils/api/TilingStatus';
import {updateDatasetTabStatuses, resetDatasetTabStatuses} from "../../reducers/datasetTabs";

interface DatasetDetailInterface {
  tabs: DatasetTabElementInterface[],
  moduleName: string,
}

const DatasetDetailTab = (Component: React.ElementType, givenProps: DatasetDetailItemInterface) => {
  return <Component {...givenProps} />
}

export default function DatasetDetail(props: DatasetDetailInterface) {
    const dispatch = useAppDispatch();
    const navigate = useNavigate()
    const tilingTabStatus = useAppSelector((state: RootState) => state.datasetTabs.tilingConfigSyncStatus)
    const [loading, setLoading] = useState(false)
    const [searchParams, setSearchParams] = useSearchParams()
    const [dataset, setDataset] = useState<Dataset>(null)
    const [tabSelected, setTabSelected] = useState(0)
    let currentDatasetId = useAppSelector(currentDataset)
    const [filteredTabs, setFilteredTabs] = useState<DatasetTabElementInterface[]>([])

    const fetchTilingStatus = () => {
      if (dataset === null) return
      let _object_type = 'dataset'
      let _object_uuid = dataset.uuid
      fetchTilingStatusAPI(_object_type, _object_uuid, (response: any, error: any) => {
         if (response) {
              let _simplification: StatusAndProgress = {
                  progress: response['simplification']['progress'],
                  status: response['simplification']['status']
              }
              let _tiling: StatusAndProgress = {
                  progress: response['vector_tiles']['progress'],
                  status: response['vector_tiles']['status']
              }
              dispatch(updateDatasetTabStatuses([_simplification, _tiling]))
         }
      })
  }

    const fetchDatasetDetail = () => {
      setLoading(true)
      axios.get(`/api/dataset-detail/${searchParams.get("id")}`).then(
        response => {
          setLoading(false)
          // append dataset name to Dataset Breadcrumbs
          let _name = response.data.dataset
          if (response.data.type) {
            _name = _name + ` (${response.data.type})`
          }
          dispatch(updateMenu({
            id: `${props.moduleName}_dataset_entities`,
            name: _name,
            link: `/${props.moduleName}/dataset_entities?id=${currentDatasetId}`
          }))
          setDataset(response.data)
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
      if (dataset === null)
        return
      let _filtered_tabs = props.tabs.filter((tab) => {
        let _has_all_perms = true
        for (let _perm of tab.permissions) {
          if (!dataset.permissions.includes(_perm)) {
            _has_all_perms = false
            break
          }
        }
        return _has_all_perms
      })
      setFilteredTabs(_filtered_tabs)
      fetchTilingStatus()
    }, [props.tabs, dataset])

    useEffect(() => {
      if (props.moduleName) {
        dispatch(setModule(props.moduleName))
      }
      dispatch(changeCurrentDataset(searchParams.get('id')))
      currentDatasetId = searchParams.get('id')
      let tab = 1
      if (searchParams.get('tab')) {
          tab = parseInt(searchParams.get('tab'))
          setTabSelected(tab)
      }
      fetchDatasetDetail()
    }, [searchParams])
  
    useEffect(() => {
      // reset previous state from other dataset
      dispatch(resetDatasetTabStatuses())
  }, [])

    const handleChange = (event: React.SyntheticEvent, newValue: number) => {
      if (newValue == 6) {
        navigate(`/upload_list?dataset=${dataset.dataset}`)
      } else if (newValue == 7) {
        navigate(`/views?dataset=${dataset.dataset}`)
      } else {
        navigate(`/${props.moduleName}/dataset_entities?id=${currentDatasetId ? currentDatasetId : searchParams.get('id')}&tab=${newValue}`)
      }
    }

    return (
        <div style={{display:'flex', flex: 1, flexDirection: 'column'}}>
            <Box sx={{ borderBottom: 1, borderColor: 'divider' }}>
                <Tabs className='DatasetTabs' value={tabSelected} onChange={handleChange} aria-label="Dataset Tab">
                  {
                    filteredTabs.map((tab, index) => {
                      if (tab.title === 'TILING CONFIG') {
                        if (tilingTabStatus === SyncStatus.Syncing) {
                          return <Tab key={index} label={tab.title}
                            icon={<CircularProgress size={18} />}
                            iconPosition={'start'}
                            {...a11yProps(index)}
                          />
                        } else if (tilingTabStatus === SyncStatus.Error) {
                          return <Tab key={index} label={tab.title}
                            icon={<ErrorIcon color='error' fontSize='small' />}
                            iconPosition={'start'}
                            {...a11yProps(index)}
                          />
                        }
                      }
                      return <Tab key={index} label={tab.title} {...a11yProps(index)} />
                    })
                  }
                </Tabs>
            </Box>
            { loading && <Skeleton variant="rectangular" height={'100%'} width={'100%'}/> }
            { !loading && (
              <Grid container sx={{ flexGrow: 1, flexDirection: 'column' }}>
                {
                filteredTabs.map((tab, index) => {
                  return <TabPanel key={index} value={tabSelected} index={index} padding={1} noPadding={tab.title==='PREVIEW'} >
                    {DatasetDetailTab(tab.element, {
                      dataset: dataset,
                      onDatasetUpdated: fetchDatasetDetail,
                      isReadOnly: !dataset.is_active
                    })}
                  </TabPanel>
                })
              }
              </Grid>
            )}
        </div>
    )
}