import React, { useState, useEffect } from 'react';
import {useSearchParams} from "react-router-dom";
import {useNavigate} from "react-router-dom";
import axios from "axios";
import Box from '@mui/material/Box';
import Grid from '@mui/material/Grid';
import Button from '@mui/material/Button';
import Tab from '@mui/material/Tab';
import Tabs from '@mui/material/Tabs';
import {useAppDispatch} from "../../app/hooks";
import {updateMenu} from "../../reducers/breadcrumbMenu";
import TabPanel, {a11yProps} from '../../components/TabPanel';
import Loading from "../../components/Loading";
import List from "../../components/List";
import { AccessRequestDetailRoute, AccessRequestListRoute } from '../routes';
import AccessRequestInterface from '../../models/access';

const FETCH_ACCESS_REQUEST_LIST = '/api/access/request/'
const getDefaultFilter = () => {
    return {
        'status': {
            'filter': true,
            'filterList': ['PENDING'],
            'filterOptions': {
                'fullWidth': true
            }
        },
        'type': {
            'filter': false,
            'display': false
        },
        'id': {
            'filter': false,
            'display': false
        },
        'name': {
            'filter': false
        },
        'requester_email': {
            'filter': false
        }
    }
}

export default function AccessRequestList() {
    const dispatch = useAppDispatch()
    const navigate = useNavigate()
    const [dataTab0, setDataTab0] = useState<AccessRequestInterface[]>([])
    const [dataTab1, setDataTab1] = useState<AccessRequestInterface[]>([])
    const [loading, setLoading] = useState(true)
    const [searchParams, setSearchParams] = useSearchParams()
    const [tabSelected, setTabSelected] = useState(0)
    const [customOptions, setCustomOptions] = useState<any>(getDefaultFilter())
    const updateSelectedTab = () => {
        let tab = 0
        if (searchParams.get('tab')) {
            tab = parseInt(searchParams.get('tab'))
            setTabSelected(tab)
        }
        let _page_title = 'New User Access Requests'
        if (tab === 1) {
            _page_title = 'Additional Permissions Access Requests'
        }
        dispatch(updateMenu({
          id: `access_request_list`,
          name: `${_page_title}`
        }))
        setCustomOptions(getDefaultFilter())
    }

    const fetchRequestList = () => {
        setLoading(true)
        let _request_type = tabSelected === 0 ? 'user' : 'permission'
        axios.get(`${FETCH_ACCESS_REQUEST_LIST}${_request_type}/list/`).then(
            response => {
              setLoading(false)
              if (tabSelected === 0)
                setDataTab0(response.data as AccessRequestInterface[])
                if (tabSelected === 1)
                  setDataTab1(response.data as AccessRequestInterface[])
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
        updateSelectedTab()
    }, [searchParams])

    useEffect(() => {
        fetchRequestList()
    }, [tabSelected])

    const handleChange = (event: React.SyntheticEvent, newValue: number) => {
        navigate(`${AccessRequestListRoute.path}?tab=${newValue}`)
    }

    const handleRowClick = (rowData: string[], rowMeta: { dataIndex: number, rowIndex: number }) => {
        navigate(`${AccessRequestDetailRoute.path}?id=${rowData[0]}`)
    }

    return (
        <div className="AdminContentMain main-data-list">
            <Box sx={{ borderBottom: 1, borderColor: 'divider' }}>
                <Tabs value={tabSelected} onChange={handleChange} aria-label="Access Request Tab">
                    <Tab key={'tab-0'} label={'NEW USERS'} {...a11yProps(0)} />
                    <Tab key={'tab-1'} label={'ADDITIONAL PERMISSIONS'} {...a11yProps(1)} />
                </Tabs>
            </Box>
            <Grid container sx={{ flexGrow: 1, flexDirection: 'column' }}>
                <TabPanel key={0} value={tabSelected} index={0} padding={1}>
                    { loading && <div className={"loading-container"}><Loading/></div> }
                    { !loading &&
                        <List
                            pageName={''}
                            listUrl={''}
                            initData={dataTab0}
                            selectionChanged={null}
                            onRowClick={handleRowClick}
                            actionData={[]}
                            excludedColumns={['type']}
                            customOptions={customOptions}
                            options={{
                                'confirmFilters': true,
                                'customFilterDialogFooter': (currentFilterList: any, applyNewFilters: any) => {
                                  return (
                                    <div style={{marginTop: '40px'}}>
                                      <Button variant="contained" onClick={() => applyNewFilters()}>Apply Filters</Button>
                                    </div>
                                  );
                                },
                              }}
                        />
                    }
                </TabPanel>
                <TabPanel key={1} value={tabSelected} index={1} padding={1}>
                    { loading && <div className={"loading-container"}><Loading/></div> }
                    { !loading &&
                        <List
                            pageName={''}
                            listUrl={''}
                            initData={dataTab1}
                            selectionChanged={null}
                            onRowClick={handleRowClick}
                            actionData={[]}
                            excludedColumns={['type']}
                            customOptions={customOptions}
                            options={{
                                'confirmFilters': true,
                                'customFilterDialogFooter': (currentFilterList: any, applyNewFilters: any) => {
                                  return (
                                    <div style={{marginTop: '40px'}}>
                                      <Button variant="contained" onClick={() => applyNewFilters()}>Apply Filters</Button>
                                    </div>
                                  );
                                },
                              }}
                        />
                    }
                </TabPanel>
            </Grid>
        </div>
    )

}