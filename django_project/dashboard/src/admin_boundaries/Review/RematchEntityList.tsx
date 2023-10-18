import React, {useEffect, useState} from "react";

import {
    Button,
    Grid
} from "@mui/material";
import axios from "axios";
import MUIDataTable from "mui-datatables";
import DetailMatchInfo from './DetailMatchInfo';
import Loading from "../../components/Loading";
import ColumnHeaderIcon from '../../components/ColumnHeaderIcon'
import AlertMessage from '../../components/AlertMessage';
import { rowsPerPageOptions } from '../../models/pagination';

const LOAD_BOUNDARY_LIST_URL = '/api/boundary-comparison-closest/'
const REMATCH_BOUNDARY_URL = '/api/boundary-compare-entities/'
const CONFIRM_REMATCH_BOUNDARY_URL = '/api/boundary-comparison-rematch/'

export interface RematchEntityListInterface {
    id: number,
    entityUploadId: string,
    handleOnBack: Function,
    onRematchConfirmed: Function
}

const COLUMNS = [
    'id',
    'name',
    'type',
    'code',
    'version',
    'level',
    'geometry_similarity_new',
    'geometry_similarity_match'
]

export default function RematchEntityList(props: RematchEntityListInterface) {
    const [loading, setLoading] = useState(true)
    const [columns, setColumns] = useState<any>([])
    const [data, setData] = useState<any[]>([])
    const [totalCount, setTotalCount] = useState<number>(0)
    const [pagination, setPagination] = useState<any>({
        page: 0,
        rowsPerPage: 5,
        sortOrder: {},
        searchText: ''
    })
    const [selectedRow, setSelectedRow] = useState(-1)
    const [rematching, setRematching] = useState(false)
    const [hasRematchedData, setHasRematchedData] = useState(false)
    const [matchInfo, setMatchInfo] = useState<any[]>([])
    const [mainBoundaryData, setMainBoundaryData] = useState<any>(null)
    const [comparisonBoundaryData, setComparisonBoundaryData] = useState<any>(null)
    const [alertMessage, setAlertMessage] = useState<string>('')

    const fetchEntities = () => {
        // fetch data
        let search_text = pagination.searchText ? pagination.searchText : ''
        axios.get(LOAD_BOUNDARY_LIST_URL + props.id +
            `/?page=${pagination.page+1}&page_size=${pagination.rowsPerPage}&search=${search_text}`
        ).then(
            response => {
                setLoading(false)
                if (response.data) {
                    setData(response.data.results)
                    setTotalCount(response.data.count)
                }
            }, error => {
                setLoading(false)
                console.log(error)
            }
        )
    }

    useEffect(() => {
        if (columns.length === 0) {
            let _columns = COLUMNS.map((column_name) => {
                let _options:any = {
                    name: column_name,
                    label: column_name.charAt(0).toUpperCase() + column_name.slice(1).replaceAll('_', ' '),
                    options: {
                        display: column_name !== 'id'
                    }
                }
                if (column_name === 'geometry_similarity_new') {
                    _options['options']['customHeadLabelRender'] = (columnMeta: any, handleToggleColumn: Function) => {
                        return (
                            <ColumnHeaderIcon title='Similarity (% new)' tooltipTitle='Geometry Similarity (% new)'
                                tooltipDescription={<p>The percentage of the new boundary area covered by the old matching boundary</p>}
                            />
                        )
                    }
                } else if (column_name === 'geometry_similarity_match') {
                    _options['options']['customHeadLabelRender'] = (columnMeta: any, handleToggleColumn: Function) => {
                        return (
                            <ColumnHeaderIcon title='Similarity (% match)' tooltipTitle='Geometry Similarity (% match)'
                                tooltipDescription={<p>The percentage of the matching boundary area covered by the new boundary</p>}
                            />
                        )
                    }
                }
                return _options
            })
            setColumns(_columns)
        }
    }, [])

    useEffect(() => {
        fetchEntities()
    }, [])

    useEffect(() => {
        fetchEntities()
    }, [pagination])

    const onRematchClick = () => {
        if (selectedRow === -1) return;
        setLoading(true)
        axios.get(REMATCH_BOUNDARY_URL + `${props.entityUploadId}/${props.id}/${selectedRow}/`).then(
            response => {
                setLoading(false)
                if (response.data) {
                    setMatchInfo([
                        props.id,
                        response.data.main_boundary_data.label,
                        response.data.comparison_boundary_data.label,
                        response.data.main_boundary_data.code,
                        response.data.comparison_boundary_data.code,
                        response.data.comparison_boundary_data.version,
                        response.data.comparison_boundary_data.level,
                        '',
                        '',
                        response.data.same_entity,
                        response.data.geometry_overlap_new,
                        response.data.geometry_overlap_old,
                        0,
                        response.data.name_similarity,
                        response.data.code_match,
                        false                        
                    ])
                    setMainBoundaryData(response.data.main_boundary_data)
                    setComparisonBoundaryData(response.data.comparison_boundary_data)
                    setHasRematchedData(true)
                }
            }, error => {
                setLoading(false)
                console.log(error)
                if (error.response) {
                    if (error.response.status == 400 && 'detail' in error.response.data) {
                      setAlertMessage('Error: ' + error.response.data['detail'])
                    }
                }
            }
        )
    }

    const onCancelClick = () => {
        props.handleOnBack();
    }

    const onRowSelected = (rowsSelected: any) => {
        setSelectedRow(rowsSelected.length ? data[rowsSelected[0]['index']]['id']: -1)
    }

    const onConfirmRematchClick = () => {
        if (selectedRow === -1) return;
        // post data
        setLoading(true)
        let postData = {
            'source_id': selectedRow,
            'entity_upload_id': props.entityUploadId
        }
        axios.post(`${CONFIRM_REMATCH_BOUNDARY_URL}${props.id}/`, postData).then(
            response => {
                setLoading(false)
                props.onRematchConfirmed({
                    'id': props.id,
                    'same_entity': matchInfo[9],
                    'old_name': matchInfo[2],
                    'old_code': matchInfo[4],
                    'old_version': matchInfo[5],
                    'old_level': matchInfo[6],
                    'geometry_overlap_new': matchInfo[10],
                    'geometry_overlap_old': matchInfo[11]
                })
            }
          ).catch(error => {
            setLoading(false)
            console.log(error)
          })
    }

    const onTableChangeState = (action:string, tableState:any) => {
        console.log('action ', action)
        switch (action) {
            case 'changePage':
                setPagination({
                    ...pagination,
                    page: tableState.page
                })
                break;
            case 'sort':
                break;
            case 'changeRowsPerPage':
                setPagination({
                    ...pagination,
                    page: 0,
                    rowsPerPage: tableState.rowsPerPage
                })
                break;
            case 'search':
                setPagination({
                    ...pagination,
                    page: 0,
                    rowsPerPage: tableState.rowsPerPage,
                    searchText: tableState.searchText
                })
                break;
            default:
          }
    }

    return (
        loading ? <div style={{ height: 300, display: "flex", alignItems: "center", justifyContent: "center" }}><Loading/></div> :
        <div>
            <AlertMessage message={alertMessage} onClose={() => setAlertMessage('')} />
            { !hasRematchedData && (
                <MUIDataTable 
                    title={''}
                    columns={columns}
                    data={data}
                    options={{
                        sort: false,
                        filter: false,
                        selectableRows: 'single',
                        selectableRowsHeader: false,
                        selectableRowsHideCheckboxes: true,
                        selectableRowsOnClick: true,
                        selectToolbarPlacement: 'none',
                        onRowSelectionChange: onRowSelected,
                        download: false,
                        print: false,
                        tableBodyMaxHeight: '400px',
                        serverSide: true,
                        page: pagination.page,
                        count: totalCount,
                        rowsPerPage: pagination.rowsPerPage,
                        rowsPerPageOptions: rowsPerPageOptions,
                        onTableChange: (action:string, tableState:any) => onTableChangeState(action, tableState),
                    }}
                />
            )}
            { hasRematchedData && (
                <Grid container flexDirection='column'>
                    <Grid item>
                        <table>
                            <tbody>
                                <DetailMatchInfo rowData={matchInfo} loading={rematching}
                                    mainBoundary={mainBoundaryData} comparisonBoundary={comparisonBoundaryData}
                                />
                            </tbody>
                        </table>
                    </Grid>
                </Grid>
            )}
            <div className="load-button-container">
                <Grid container direction="row"
                    justifyContent="space-between"
                    spacing={1}>
                    <Grid item>
                        { hasRematchedData && (
                            <Button variant="outlined" onClick={() => setHasRematchedData(false)}>
                                Select other to compare
                            </Button>
                        )}
                    </Grid>
                    <Grid item>
                        <Grid container direction="row" 
                            justifyContent="flex-end" 
                            alignItems="center"
                            spacing={2} sx={{marginTop: '10px'}}>
                            <Grid item>
                                { !hasRematchedData && (
                                    <Button disabled={selectedRow === -1} onClick={onRematchClick} variant="contained">
                                        Rematch
                                    </Button>
                                )}
                                { hasRematchedData && (
                                    <Button onClick={onConfirmRematchClick} variant="contained">
                                        Confirm
                                    </Button>
                                )}
                            </Grid>
                            <Grid item>
                                <Button onClick={onCancelClick} variant="outlined">
                                    Cancel
                                </Button>
                            </Grid>
                        </Grid>
                    </Grid>
                </Grid>
            </div>
        </div>
    )
}