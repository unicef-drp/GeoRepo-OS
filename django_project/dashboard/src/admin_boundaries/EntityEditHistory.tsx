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
    const [customColumnOptions, setCustomColumnOptions] = useState({
        'Status': {
            filter: true,
            sort: true,
            display: true,
            filterOptions: {
              fullWidth: true,
            }
        },
    })
    const excludedColumns = ['object_id', 'dataset_id', 'progress', 'total_count', 'success_count', 'error_count']

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
        const objectId = rowData[5]
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
                            excludedColumns={excludedColumns}
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
