import React, {useEffect, useState, useRef, useCallback} from 'react';
import MUIDataTable, { MUISortOptions, debounceSearchRender } from "mui-datatables";
import FilterAlt from '@mui/icons-material/FilterAlt';
import {
    Grid,
    Select,
    SelectChangeEvent,
    Skeleton} from "@mui/material";

import MenuItem from "@mui/material/MenuItem";
import ReviewMap from "./DetailMap";
import axios from "axios";
import ResizeTableEvent from "../../components/ResizeTableEvent"
import {TABLE_OFFSET_HEIGHT} from '../../components/List'
import '../../styles/DetailMatchTable.scss';
import Loading from "../../components/Loading";
import Scrollable from '../../components/Scrollable';
import { ReviewTabInterface } from '../../models/upload';
import PaginationInterface, { getDefaultPagination, rowsPerPageOptions } from '../../models/pagination';


const COLUMNS = [
    'id',
    'code',
    'type'
]

const COLUMNS_FILTERABLE:string[] = []

interface TableRowInterface {
    id: number,
    code: string,
    type: string
}

interface TableFilterInterface {
    search_text: string
}

const API_URL = '/api/boundary-lines-match-table/'
const GEOMETRIES_URL = '/api/boundary-lines-geometry/'

const FilterIcon: any = FilterAlt

export default function DetailMatchTable(props: ReviewTabInterface) {
    const [columns, setColumns] = useState<any>([])
    const [data, setData] = useState<TableRowInterface[]>([])
    const [totalCount, setTotalCount] = useState<number>(0)
    const [pagination, setPagination] = useState<PaginationInterface>(getDefaultPagination())
    const [filter, setFilter] = useState<TableFilterInterface>({
        search_text: ''
    })
    const [selectedType, setSelectedType] = useState<string | null>(props.uploadSession?.types ? props.uploadSession?.types[0] : null)
    const [loading, setLoading] = useState<boolean>(true)
    const ref = useRef(null)
    const [tableHeight, setTableHeight] = useState(0)
    const [boundaryBbox, setBoundaryBbox] = useState<any>(null)
    const [mainBoundary, setMainBoundary] = useState<any>(null)
    const axiosSource = useRef(null)
    const newCancelToken = useCallback(() => {
        axiosSource.current = axios.CancelToken.source();
        return axiosSource.current.token;
      }, [])

    const fetchingDetailData = () => {
        if (axiosSource.current) axiosSource.current.cancel()
        let cancelFetchToken = newCancelToken()
        setLoading(true)
        let sort_by = pagination.sortOrder.name ? pagination.sortOrder.name : ''
        let sort_direction = pagination.sortOrder.direction ? pagination.sortOrder.direction : ''
        let _additional_filters = ''
        for (const [key, value] of Object.entries(filter)) {
            if (value) {
                _additional_filters = _additional_filters + `&${key}=${value}`
            }
        }
        // API call here based on selectedLevel
        axios.get(`${API_URL}${props.uploadSession.entityUploadId}/${selectedType}/?`+
            `page=${pagination.page+1}&page_size=${pagination.rowsPerPage}&sort_by=${sort_by}&sort_direction=${sort_direction}`+
            `${_additional_filters}`,
        {
            cancelToken: cancelFetchToken
        }).then(
            response => {
                setLoading(false)
                setData(response.data.results as TableRowInterface[])
                setTotalCount(response.data.count)
            },
            error => {
                setLoading(false)
                console.error(error)
            }
        )
    }

    const fetchingDetailGeomEntity = (id: number) => {
        axios.get(`${GEOMETRIES_URL}${id}`).then(
            response => {
                setBoundaryBbox(response.data['bbox'])
                setMainBoundary(response.data['geom'])
            },
            error => {
                setLoading(false)
                console.error(error)
            }
        )
    }

    useEffect(() => {
        setColumns(COLUMNS.map((column_name) => {
            let _options:any = {
                name: column_name,
                label: column_name.charAt(0).toUpperCase() + column_name.slice(1).replaceAll('_', ' '),
                options: {
                    display: column_name !== 'id',
                    filter: COLUMNS_FILTERABLE.includes(column_name),
                    sort: column_name === 'code' 
                }
            }
            return _options
        }))
        fetchingDetailData()
    }, [])

    useEffect(() => {
        fetchingDetailData()
        // set initial bbox
        if (props.uploadSession.bbox)
            setBoundaryBbox(props.uploadSession.bbox)
    }, [selectedType])

    useEffect(() => {
        fetchingDetailData()
    }, [pagination, filter])

    const changeType = (newType: string) => {
        setLoading(true)
        setSelectedType(newType)
        setData([])
        setLoading(true)
    }

    const onRowSelected = (rowsSelected: any) => {
        if (rowsSelected) {
            let _idx = rowsSelected[0].dataIndex
            if (data && _idx < data.length)
                fetchingDetailGeomEntity(data[_idx].id)
        }
    }

    const onTableChangeState = (action:string, tableState:any) => {
        switch (action) {
            case 'changePage':
                setPagination({
                    ...pagination,
                    page: tableState.page
                })
                break;
            case 'sort':
                setPagination({
                    ...pagination,
                    page: 0,
                    sortOrder: tableState.sortOrder
                })
                break;
            case 'changeRowsPerPage':
                setPagination({
                    ...pagination,
                    page: 0,
                    rowsPerPage: tableState.rowsPerPage
                })
                break;
            default:
          }
    }

    const handleSearchOnChange = (search_text: string) => {
        setPagination({
            ...pagination,
            page: 0,
            sortOrder: {}
        })
        setFilter({...filter, 'search_text':search_text})
    }

    return (
        <Scrollable>
         <Grid className={'detail-match'} container spacing={2} flexWrap='nowrap'>
            <Grid item xs={12} md={6} className={'detail-match-table'} ref={ref}
                sx={{flexGrow:{ sm: 1}}}>
                {!loading && <ResizeTableEvent containerRef={ref} onBeforeResize={() => setTableHeight(0)}
                    onResize={(clientHeight:number) => {
                        setTableHeight(clientHeight - TABLE_OFFSET_HEIGHT)
                    }} />}
                <MUIDataTable columns={columns} data={data}
                    title={<div>
                        <Select
                            disabled={loading}
                            onChange={(event: SelectChangeEvent) => changeType(event.target.value)}
                            value={selectedType}
                            className={'type-select'}
                            sx={{width:'100%'}}
                            >
                            {props.uploadSession?.types?.map((type) => {
                                return <MenuItem key={type}
                                                value={type}>Type {type}</MenuItem>
                            })}
                        </Select>
                    </div>}
                    options={{
                        serverSide: true,
                        page: pagination.page,
                        count: totalCount,
                        rowsPerPage: pagination.rowsPerPage,
                        rowsPerPageOptions: rowsPerPageOptions,
                        sortOrder: pagination.sortOrder as MUISortOptions,
                        jumpToPage: true,
                        onTableChange: (action:string, tableState:any) => onTableChangeState(action, tableState),
                        customSearchRender: debounceSearchRender(500),
                        selectableRows: 'single',
                        selectableRowsHeader: false,
                        selectableRowsHideCheckboxes: true,
                        selectableRowsOnClick: true,
                        selectToolbarPlacement: 'none',
                        onRowSelectionChange: onRowSelected,
                        expandableRows: false,
                        expandableRowsHeader: false,
                        setTableProps: () => ({className: 'review-match-table'}),
                        fixedHeader: true,
                        fixedSelectColumn: false,
                        tableBodyHeight: `${tableHeight}px`,
                        tableBodyMaxHeight: `${tableHeight}px`,
                        textLabels: {
                            body: {
                                noMatch: loading ?
                                    <Loading /> :
                                    'Sorry, there is no matching data to display',
                            },
                        },
                        filter: false,
                        onSearchChange: (searchText: string) => {
                            handleSearchOnChange(searchText)
                        },
                        searchText: filter.search_text,
                        searchOpen: (filter.search_text != null && filter.search_text.length > 0),
                }}
                components={{
                    icons: {
                      FilterIcon
                    }
                }}/>
            </Grid>
            <Grid item xs={12} md={6}
                sx={{flexGrow:{ sm: 1}}}>
                {data.length > 0 ?
                    <ReviewMap bbox={boundaryBbox} mainBoundary={mainBoundary}
                        selectedType={selectedType}
                        uploadSession={props.uploadSession}
                        /> :
                    <Skeleton variant="rectangular" width={'100%'}/>
                 }
            </Grid>
        </Grid>
    </Scrollable>
    )
}
