import React, { useEffect, useState } from "react";
import {useNavigate} from "react-router-dom";
import { Box, Button } from "@mui/material";
import axios from "axios";
import Scrollable from '../components/Scrollable';
import List from "../components/List";
import Loading from "../components/Loading";
import { EntityEditHistoryItemInterface } from "../models/entity";

const FETCH_HISTORY_LIST_URL = '/api/entity-edit-history/'

export default function EntityEditHistory(props: any) {
    const {dataset} = props
    const navigate = useNavigate()
    const [loading, setLoading] = useState(false)
    const [data, setData] = useState<EntityEditHistoryItemInterface[]>([])
    const customColumnOptions = {
        'epoch': {
            'label': 'Date',
            'customBodyRender': (value: any, tableMeta: any, updateValue: any) => {
                let rowData = tableMeta.rowData
                return (
                    <span>{new Date(rowData[0] * 1000).toDateString()}</span>
                )
            },
            'filter': false
        },
        'user_first_name': {
            'name': 'user_first_name',
            'label': 'User',
            'customBodyRender': (value: any, tableMeta: any, updateValue: any) => {
                let rowData = tableMeta.rowData
                let _name = rowData[1]
                let _lastName = rowData[2]
                if (_lastName) {
                    _name = _name + ' ' + _lastName
                }
                return (
                    <span>{_name ? _name : '-'}</span>
                )
            },
            'filter': false
        },
        'object_id': {
            'display': false,
            'filter': false
        },
        'user_last_name': {
            'display': false,
            'filter': false
        },
        'type': {
            'name': 'type',
            'label': 'Type',
            'filter': true,
            'filterOptions': {
                fullWidth: true,
            },
            'customBodyRender': (value: any, tableMeta: any, updateValue: any) => {
                let rowData = tableMeta.rowData
                let _type = rowData[3]
                if (_type !== 'Batch') return <span>{value}</span>
                return <span className="TableCellLink">{value}</span>
            }
        },
        'status_text': {
            'name': 'status_text',
            'label': 'Status',
            'filter': true,
            'filterOptions': {
                fullWidth: true,
            }
        },
        'summary_text': {
            'name': 'summary_text',
            'label': 'Summary',
            'filter': false,
            'sort': false
        }
    }

    const fetchData = () => {
        setLoading(true)
        axios.get(FETCH_HISTORY_LIST_URL + `?dataset_id=${dataset.id}`).then(response => {
            if (response.data) {
                setData(response.data as EntityEditHistoryItemInterface[])
            } else {
                setData([])
            }
            setLoading(false)
        }).catch(error => {
            setLoading(false)
            console.log(error)
            let _message = 'Unable to fetch entity edit history!'
            if (error.response) {
                if ('detail' in error.response.data) {
                    _message = error.response.data.detail
                }
            }
            alert(_message)
        })
    }

    useEffect(() => {
        fetchData()
    }, [dataset])

    const handleRowClick = (rowData: string[], rowMeta: { dataIndex: number, rowIndex: number }) => {
        const type = data[rowMeta.dataIndex].type
        if (type !== 'Batch') return;
        const objectId = rowData[4]
        let _navigate_to = `/admin_boundaries/edit_entity/wizard?session=${objectId}&dataset=${dataset.id}`
        navigate(_navigate_to)
    }

    return (
        <Scrollable>
            <Box sx={{ display: 'flex', flexDirection: 'column', height: '100%', overflowY: 'auto' }}>
                <Box sx={{ flexGrow: 1, display: 'flex', flexDirection: 'column' }}>
                    {!loading ? 
                        <List
                            pageName={'Entity Edit History'}
                            listUrl={''}
                            initData={data as any[]}
                            selectionChanged={null}
                            onRowClick={handleRowClick}
                            customOptions={customColumnOptions}
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
                        /> : <Loading/>}
                </Box>
            </Box>
        </Scrollable>
    )
}
