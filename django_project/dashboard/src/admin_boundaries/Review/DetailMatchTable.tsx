import React, {useEffect, useState, useRef, useCallback} from 'react';
import MUIDataTable, {debounceSearchRender, MUISortOptions} from "mui-datatables";
import FilterAlt from '@mui/icons-material/FilterAlt';
import {
    Grid,
    Select,
    SelectChangeEvent,
    Skeleton,
    Modal,
    Box,
    Button,
    Tooltip,
    FormLabel,
    FormGroup,
    TextField,
    Typography,
} from "@mui/material";
import Table from '@mui/material/Table';
import TableBody from '@mui/material/TableBody';
import TableCell from '@mui/material/TableCell';
import TableContainer from '@mui/material/TableContainer';
import TableHead from '@mui/material/TableHead';
import TableRow from '@mui/material/TableRow';
import Paper from '@mui/material/Paper';
import MenuItem from "@mui/material/MenuItem";
import ReviewMap from "./DetailMap";
import axios from "axios";
import RematchEntityList from './RematchEntityList';
import ResizeTableEvent from "../../components/ResizeTableEvent"
import InfoIcon from '@mui/icons-material/Info';
import {TABLE_OFFSET_HEIGHT} from '../../components/List'
import '../../styles/DetailMatchTable.scss';
import Loading from "../../components/Loading";
import ColumnHeaderIcon from '../../components/ColumnHeaderIcon'
import AlertDialog from '../../components/AlertDialog'
import {postData} from "../../utils/Requests";
import Scrollable from '../../components/Scrollable';
import { ReviewTabInterface, DISABLED_STATUS_LIST, BoundaryData } from '../../models/upload';
import PaginationInterface from '../../models/pagination';
import CircleIcon from '@mui/icons-material/Circle';
import { useKeyPress } from '../../components/UseKeyPress';
import { rowsPerPageOptions } from '../../models/pagination';


const COLUMNS = [
    'id',
    'new_name',
    'default_new_code',
    'matching_name',
    'new_code',
    'matching_code',
    'matching_version',
    'matching_level',
    'parent_name',
    'parent_code',
    'new_area',
    'old_area',
    'new_perimeter',
    'old_perimeter',
    'same_entity',
    'geometry_similarity_new',
    'geometry_similarity_matching',
    'distance',
    'name_similarity',
    'code_match',
    'is_parent_rematched',
    'default_old_code',
    'old_parent_name',
    'old_parent_code',
    'ucode_version'
]

const COLUMNS_FILTERABLE = [
    'same_entity',
    'geometry_similarity_new',
    'geometry_similarity_matching',
    'distance',
    'name_similarity',
    'code_match',
    'is_parent_rematched'
]

const COLUMNS_HIDDEN = [
    'id',
    'is_parent_rematched',
    'default_old_code',
    'old_parent_name',
    'old_parent_code',
    'ucode_version'
]

const BOOLEAN_COLUMN_FILTER_VALUES = [
    'No',
    'Yes'
]

const getDefaultPagination = ():PaginationInterface => {
    return {
        page: 0,
        rowsPerPage: 20,
        sortOrder: {}
    }
}

interface TableRowInterface {
    id: number,
    new_name: string,
    default_new_code: string,
    matching_name?: string,
    new_code: string,
    matching_code?: string,
    matching_version?: string,
    matching_level?: string,
    parent_name?: string,
    parent_code?: string,
    same_entity: string,
    geometry_similarity_new: number,
    geometry_similarity_matching: number,
    distance?: number,
    name_similarity?: number,
    code_match?: string,
    is_parent_rematched?: boolean,
    new_area: number,
    old_area: number,
    new_perimeter: number,
    old_perimeter: number,
    default_old_code?: string,
    old_parent_name?: string,
    old_parent_code?: string,
    ucode_version?: string
}

interface TableFilterInterface {
    search_text: string,
    same_entity?: boolean,
    code_match?: boolean,
    is_parent_rematched?: boolean,
    min_geometry_similarity_new?: number,
    max_geometry_similarity_new?: number,
    min_distance?: number,
    max_distance?: number,
    min_name_similarity?: number,
    max_name_similarity?: number
}

interface MatchCompactTableProps {
    data?: TableRowInterface,
    selectedLevel: string,
    loading: boolean
}

interface ConceptButtonProps {
    data?: TableRowInterface,
    loading: boolean,
    onClick: () => void
}

const API_URL = '/api/boundary-comparison-match-table/'
const GEOMETRIES_URL = '/api/boundary-comparison-geometry/'
const SWAP_ENTITY_CONCEPT_URL = '/api/boundary-swap-entity-concept/'

const FilterIcon: any = FilterAlt

const checkMatchingLevel = (matchingLevel: string, selectedLevel: string, loading: boolean) => {
    if (loading || matchingLevel === undefined || matchingLevel === null || matchingLevel === '' || selectedLevel === '') {
        return true
    }
    if (matchingLevel !== selectedLevel) {
        return false
    }
    return true
}


function MatchCompactTable(props: MatchCompactTableProps) {
    
    const displayTableValue = (value: any) => {
        if (value === undefined || value === null || value === '') {
            return '-'
        }
        return value
    }

    let circleAdditionalClass = props.loading ? '' : 'GreenCircle'
    if (props.data?.same_entity === 'No') {
        circleAdditionalClass = 'NoComparison'
    }

    return (
        <TableContainer component={Paper}>
          <Table aria-label="matching table" className='DetailMatchCompactTable'>
            <TableHead>
              <TableRow>
                <TableCell className='CompactTableHeader'></TableCell>
                <TableCell className='NewEntityHeader'>New Entity</TableCell>
                <TableCell className='MatchingEntityHeader'>Matching Entity</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
                <TableRow key={'name'} className='DetailMatchRow'>
                  <TableCell>Name</TableCell>
                  <TableCell>{displayTableValue(props.data?.new_name)}</TableCell>
                  <TableCell>{displayTableValue(props.data?.matching_name)}</TableCell>
                </TableRow>
                <TableRow key={'default-code'} className='DetailMatchRow'>
                  <TableCell>Default Code</TableCell>
                  <TableCell>{displayTableValue(props.data?.default_new_code)}</TableCell>
                  <TableCell>{displayTableValue(props.data?.default_old_code)}</TableCell>
                </TableRow>
                <TableRow key={'ucode'} className='DetailMatchRow'>
                  <TableCell>Unique Code</TableCell>
                  <TableCell>{displayTableValue(props.data?.new_code)}</TableCell>
                  <TableCell>{displayTableValue(props.data?.matching_code)}</TableCell>
                </TableRow>
                <TableRow key={'level'} className={'DetailMatchRow '}>
                  <TableCell>Level</TableCell>
                  <TableCell>{props.selectedLevel} {!checkMatchingLevel(props.data?.matching_level, props.selectedLevel, props.loading) ?  <CircleIcon className={`MatchingStatusIcon WarningCircle`} />: null}</TableCell>
                  <TableCell>{displayTableValue(props.data?.matching_level)} {!checkMatchingLevel(props.data?.matching_level, props.selectedLevel, props.loading) ?  <CircleIcon className={`MatchingStatusIcon WarningCircle`} />: null}</TableCell>
                </TableRow>
                <TableRow key={'version'} className='DetailMatchRow'>
                  <TableCell>Version</TableCell>
                  <TableCell>{displayTableValue(props.data?.ucode_version)}</TableCell>
                  <TableCell>{displayTableValue(props.data?.matching_version)}</TableCell>
                </TableRow>
                <TableRow key={'parent_name'} className='DetailMatchRow'>
                  <TableCell>Parent Name</TableCell>
                    <TableCell>{displayTableValue(props.data?.parent_name)}</TableCell>
                    <TableCell>{displayTableValue(props.data?.old_parent_name)}</TableCell>
                </TableRow>
                <TableRow key={'parent_ucode'} className='DetailMatchRow'>
                  <TableCell>Parent Code</TableCell>
                    <TableCell>{displayTableValue(props.data?.parent_code)}</TableCell>
                    <TableCell>{displayTableValue(props.data?.old_parent_code)}</TableCell>
                </TableRow>
                <TableRow key={'area'} className='DetailMatchRow'>
                  <TableCell>Area</TableCell>
                  <TableCell>{props.data?.new_area} km2</TableCell>
                  <TableCell>{props.data?.old_area} km2</TableCell>
                </TableRow>
                <TableRow key={'perimeter'} className='DetailMatchRow'>
                  <TableCell>Perimeter</TableCell>
                  <TableCell>{displayTableValue(props.data?.new_perimeter)}</TableCell>
                  <TableCell>{displayTableValue(props.data?.old_perimeter)}</TableCell>
                </TableRow>
                <TableRow key={'similarity'} className='DetailMatchRow'>
                  <TableCell>Similarity</TableCell>
                  <TableCell>{displayTableValue(props.data?.geometry_similarity_new)} (% new) <CircleIcon className={`MatchingStatusIcon ${circleAdditionalClass}`} /></TableCell>
                  <TableCell>{displayTableValue(props.data?.geometry_similarity_matching)} (% match) <CircleIcon className={`MatchingStatusIcon ${circleAdditionalClass}`} /></TableCell>
                </TableRow>
                <TableRow key={'same_entity'} className='DetailMatchRow'>
                  <TableCell>Same Entity</TableCell>
                  <TableCell colSpan={2} className='SingleCell'>{displayTableValue(props.data?.same_entity)} <CircleIcon className={`MatchingStatusIcon ${circleAdditionalClass}`} /></TableCell>
                </TableRow>
                <TableRow key={'distance'} className='DetailMatchRow'>
                  <TableCell>Distance</TableCell>
                  <TableCell colSpan={2} className='SingleCell'>{displayTableValue(props.data?.distance)} <CircleIcon className={`MatchingStatusIcon ${circleAdditionalClass}`} /></TableCell>
                </TableRow>
                <TableRow key={'name_similarity'} className='DetailMatchRow'>
                  <TableCell>Name Similarity</TableCell>
                  <TableCell colSpan={2} className='SingleCell'>{displayTableValue(props.data?.name_similarity)} <CircleIcon className={`MatchingStatusIcon ${circleAdditionalClass}`} /></TableCell>
                </TableRow>
                <TableRow key={'code_match'} className='DetailMatchRow'>
                  <TableCell>Code Match</TableCell>
                  <TableCell colSpan={2} className='SingleCell'>{displayTableValue(props.data?.code_match)} <CircleIcon className={`MatchingStatusIcon ${circleAdditionalClass}`} /></TableCell>
                </TableRow>
            </TableBody>
          </Table>
        </TableContainer>
      );
}

function ConceptButton(props: ConceptButtonProps) {
    const sameEntity = props.data && props.data.same_entity  && props.data.same_entity.toLowerCase() === 'yes'
    const newEntityLabel = 'Change to New Concept'
    const existingEntityLabel = 'Change to Same Concept'
    const hasComparisonBoundary = props.data && props.data.matching_code
    const isDisabled = props.loading || !hasComparisonBoundary
    let className = sameEntity ? 'GreenCell': 'GrayCell'
    if (isDisabled) {
        className = ''
    }
    return (
        <Button disabled={isDisabled} variant="contained" className={className}
            onClick={props.onClick}
            title={sameEntity ? newEntityLabel: existingEntityLabel}>
            Concept
        </Button>
    )
}

export default function DetailMatchTable(props: ReviewTabInterface) {
    const [columns, setColumns] = useState<any>([])
    const [data, setData] = useState<TableRowInterface[]>([])
    const [totalCount, setTotalCount] = useState<number>(0)
    const [totalPage, setTotalPage] = useState<number>(1)
    const [pagination, setPagination] = useState<PaginationInterface>(getDefaultPagination())
    const [filter, setFilter] = useState<TableFilterInterface>({
        search_text: ''
    })
    const [selectedLevel, setSelectedLevel] = useState<string | null>(props.uploadSession?.levels ? props.uploadSession?.levels[0] : null)
    const [loading, setLoading] = useState<boolean>(true)
    const [mainBoundary, setMainBoundary] = useState<any>(null)
    const [comparisonBoundary, setComparisonBoundary] = useState<any>(null)
    const [boundaryBbox, setBoundaryBbox] = useState<any>(null)
    // index of selected rows
    const [rowsSelected, setRowsSelected] = useState<any[]>([])
    // data of selected row (single)
    const [selectedRowData, setSelectedRowData] = useState<TableRowInterface>(null)
    const [fetchingSummary, setFetchingSummary] = useState<boolean>(false)
    const [mainBoundaryData, setMainBoundaryData] = useState<BoundaryData>(null)
    const [comparisonBoundaryData, setComparisonBoundaryData] = useState<BoundaryData>(null)
    const ref = useRef(null)
    const [tableHeight, setTableHeight] = useState(0)
    const [openRematch, setOpenRematch] = useState(false)
    const [rematchEntityId, setRematchEntityId] = useState(null)
    const [swapBoundaryId, setSwapBoundaryId] = useState(null)
    const [alertDialogLoading, setAlertDialogLoading] = useState<boolean>(false)
    const [alertDialogTitle, setAlertDialogTitle] = useState<string>('')
    const [alertDialogDescription, setAlertDialogDescription] = useState<string>('')
    const axiosSource = useRef(null)
    const newCancelToken = useCallback(() => {
        axiosSource.current = axios.CancelToken.source();
        return axiosSource.current.token;
      }, [])
    // 0: first selection, 1: from last index
    const [initSelection, setInitSelection] = useState(0)
    const isReadOnly = Boolean(DISABLED_STATUS_LIST.includes(props.uploadSession.uploadStatus))
    // listen to keyboard arrows
    const downPress = useKeyPress("ArrowDown");
    const upPress = useKeyPress("ArrowUp");

    const fetchingComparisonData = () => {
        if (axiosSource.current) axiosSource.current.cancel()
        let cancelFetchToken = newCancelToken()
        setData([])
        setLoading(true)
        let sort_by = pagination.sortOrder.name ? pagination.sortOrder.name : ''
        let sort_direction = pagination.sortOrder.direction ? pagination.sortOrder.direction : ''
        let _additional_filters = ''
        for (const [key, value] of Object.entries(filter)) {
            if (key.indexOf('similarity') >= 0 || key.indexOf('distance') >= 0) {
                _additional_filters = _additional_filters + `&${key}=${value}`
            } else if (value) {
                _additional_filters = _additional_filters + `&${key}=${value}`
            }
        }
        // API call here based on selectedLevel
        axios.get(`${API_URL}${props.uploadSession.entityUploadId}/${selectedLevel}/?`+
            `page=${pagination.page+1}&page_size=${pagination.rowsPerPage}&sort_by=${sort_by}&sort_direction=${sort_direction}`+
            `${_additional_filters}`,
        {
            cancelToken: cancelFetchToken
        }).then(
            response => {
                setLoading(false)
                setData(response.data.results as TableRowInterface[])
                if (response.data.results && response.data.results.length) {
                    // depends on initSelection
                    if (initSelection === 1) {
                        // start from
                        setInitSelection(0)
                        setRowsSelected([response.data.results.length - 1])
                    } else {
                        setRowsSelected([0])
                    }
                }
                setTotalCount(response.data.count)
                setTotalPage(response.data.total_page)
            },
            error => {
                if (!axios.isCancel(error)) {
                    console.log(error)
                    setLoading(false)
                }
            }
        )
    }

    useEffect(() => {
        setColumns(COLUMNS.map((column_name) => {
            let _options:any = {
                name: column_name,
                label: column_name.charAt(0).toUpperCase() + column_name.slice(1).replaceAll('_', ' '),
                options: {
                    display: !COLUMNS_HIDDEN.includes(column_name),
                    filter: COLUMNS_FILTERABLE.includes(column_name),
                    setCellProps: (value: string, rowIndex: number, columnIndex: number) => {
                        let className = ''
                        if (column_name.indexOf('similarity') >= 0) {
                            className = 'GreenCell'
                        } else if (column_name.indexOf('code_match') >= 0) {
                            className = 'GreenCell'
                        } else if (column_name.indexOf('distance') >= 0) {
                            className = 'GreenCell'
                        } else if (column_name === 'same_entity') {
                            className = value.toLowerCase() === 'yes' ? 'GreenCell' : 'GrayCell'
                        }
                        return {
                          className: className,
                        };
                    }
                }
            }
            if (column_name === 'parent_name') {
                _options['options']['customBodyRender'] = (value: any, tableMeta: any) => {
                    let _idx = COLUMNS.findIndex((col) => col === 'is_parent_rematched')
                    let has_rematched = tableMeta.rowData[_idx]
                    return (
                        <div style={{display:'flex', alignItems:'center' }}>
                            <span>
                                { `${value}` }
                            </span>
                            {has_rematched && (
                                <Tooltip title={`The parent has been rematched`}>
                                    <InfoIcon fontSize="small" color="warning" sx={{ ml: '10px' }} />
                                </Tooltip>
                            )}
                        </div>
                    )
                }
            } else if (column_name.indexOf('similarity') >= 0 || column_name.indexOf('distance') >= 0) {
                // override header name for similarity columns
                if (column_name === 'geometry_similarity_new') {
                    _options['label'] = 'Similarity (% new)'
                    _options['options']['customHeadLabelRender'] = (columnMeta: any, handleToggleColumn: Function) => {
                        return <ColumnHeaderIcon title='Similarity (% new)' tooltipTitle='Geometry Similarity (% new)'
                            tooltipDescription={<p>The percentage of the new boundary area covered by the matching boundary</p>}
                        />
                    }
                    _options['options']['setCellHeaderProps'] = () => ({
                        style: {
                            whiteSpace: "nowrap",
                        }
                    })
                } else if (column_name === 'geometry_similarity_matching') {
                    _options['label'] = 'Similarity (% match)'
                    _options['options']['customHeadLabelRender'] = (columnMeta: any, handleToggleColumn: Function) => {
                        return <ColumnHeaderIcon title='Similarity (% match)' tooltipTitle='Geometry Similarity (% match)'
                            tooltipDescription={<p>The percentage of the matching boundary area covered by the new boundary</p>}
                        />
                    }
                    _options['options']['setCellHeaderProps'] = () => ({
                        style: {
                            whiteSpace: "nowrap",
                        }
                    })
                }
                _options['options']['searchable'] = false
                _options['options']['filter'] = true
                _options['options']['filterType'] = 'custom'
                _options['options']['filterOptions'] = {
                    logic(val:any, filters:any) {
                        // if (filters[0] && filters[1]) {
                        //     let _val = parseFloat(val)
                        //     return !(parseFloat(filters[0]) <= _val && _val <= parseFloat(filters[1]))
                        // }
                        
                        return false;
                    },
                    display: (filterList: any, onChange: any, index: any, column: any) => (
                        <div>
                            <FormLabel>{_options.label} between</FormLabel>
                            <FormGroup row style={{alignItems: 'center'}}>
                                <TextField
                                    type='number'
                                    label='min'
                                    value={filterList[index][0] || ''}
                                    onChange={event => {
                                        filterList[index][0] = event.target.value;
                                        onChange(filterList[index], index, column);
                                    }}
                                    style={{ width: '35%', marginRight: '2%' }}
                                />
                                <Typography>and</Typography>
                                <TextField
                                    type='number'
                                    label='max'
                                    value={filterList[index][1] || ''}
                                    onChange={event => {
                                        filterList[index][1] = event.target.value;
                                        onChange(filterList[index], index, column);
                                    }}
                                    style={{ width: '35%', marginLeft: '2%' }}
                                />
                            </FormGroup>
                        </div>
                    )
                }
                _options['options']['customFilterListOptions'] = {
                    render: (v:any):any => {
                        return v && v.length && v[0] && v[1]?[`${_options.label} between ${v[0]} and ${v[1]}`]:[]
                    },
                    update: (filterList:any, filterPos:any, index:any) => {
                        filterList[index] = []
                        return filterList;
                    }
                }
            } else if (column_name === 'same_entity' || column_name === 'code_match' || column_name === 'is_parent_rematched') {
                _options['options']['filterOptions'] = {
                    names: BOOLEAN_COLUMN_FILTER_VALUES
                }
                _options['options']['customFilterListOptions'] = {
                    render: (v:any) => `${_options['label']} ${v}`
                }
            }

            // sticky columns
            if (column_name === 'new_name') {
                _options['options']['setCellProps'] = () => ({
                    className: 'StickyCell',
                    style: {
                        position: "sticky",
                        left: "0",
                        zIndex: 100,
                        minWidth: 140,
                        maxWidth: 140
                    }
                })
                _options['options']['setCellHeaderProps'] = () => ({
                    style: {
                        position: "sticky",
                        left: "0",
                        background: "white",
                        zIndex: 101,
                        minWidth: 140,
                        maxWidth: 140
                    }
                })
            } else if (column_name === 'default_new_code') {
                _options['options']['setCellProps'] = () => ({
                    className: 'StickyCell',
                    style: {
                        whiteSpace: "nowrap",
                        position: "sticky",
                        left: "156px",
                        zIndex: 100
                    }
                })
                _options['options']['setCellHeaderProps'] = () => ({
                    style: {
                        whiteSpace: "nowrap",
                        position: "sticky",
                        left: "156px",
                        background: "white",
                        zIndex: 101
                    }
                })
            } else if (column_name === 'matching_name' || column_name === 'parent_name') {
                _options['options']['setCellProps'] = () => ({
                    style: {
                        whiteSpace: "normal",
                        minWidth: 140,
                        maxWidth: 140
                    }
                })
                _options['options']['setCellHeaderProps'] = () => ({
                    style: {
                        whiteSpace: "normal",
                        minWidth: 140,
                        maxWidth: 140
                    }
                })
            }

            return _options
        }))
        fetchingComparisonData()
    }, [])

    useEffect(() => {
        resetComparisonData()
        fetchingComparisonData()
    }, [pagination, filter])

    useEffect(() => {
        fetchingComparisonData()
    }, [selectedLevel])

    useEffect(() => {
        if (rowsSelected && rowsSelected.length) {
            let _idx = rowsSelected[0]
            if (data && _idx < data.length) {
                setSelectedRowData(data[_idx])
            }
        } else {
            setSelectedRowData(null)
        }
    }, [rowsSelected])

    useEffect(() => {
        if (selectedRowData && selectedRowData.id) {
            setBoundaryBbox(null)
            fetchSummary(selectedRowData.id)
        }
    }, [selectedRowData])

    useEffect(() => {
        onNextRow()
    }, [downPress])

    useEffect(() => {
        onPreviousRow()
    }, [upPress])

    const resetComparisonData = () => {
        // reset variables
        setRowsSelected([])
        setMainBoundary(null)
        setComparisonBoundary(null)
        setMainBoundaryData(null)
        setComparisonBoundaryData(null)
    }

    const changeLevel = (newLevel: string) => {
        resetComparisonData()
        setLoading(true)
        setData([])
        setSelectedLevel(newLevel)
        setFetchingSummary(false)
        setLoading(true)
    }

    const fetchSummary = (boundaryId: number) => {
        setFetchingSummary(true)
        axios.get(`${GEOMETRIES_URL}${boundaryId}`).then(
            response => {
                if (response.data['main_boundary_geom']) {
                    setMainBoundary(response.data['main_boundary_geom'])
                    setBoundaryBbox(response.data['bbox'])
                }
                if (response.data['main_boundary_data']) {
                    setMainBoundaryData(response.data['main_boundary_data'] as BoundaryData)
                }
                if (response.data['comparison_boundary_geom']) {
                    setComparisonBoundary(response.data['comparison_boundary_geom'])
                } else {
                    setComparisonBoundary(null)
                }
                if (response.data['comparison_boundary_data']) {
                    setComparisonBoundaryData(response.data['comparison_boundary_data'] as BoundaryData)
                }
                setFetchingSummary(false)
            }, error => {
                console.log(error)
                setFetchingSummary(false)
            }
        )
    }

    const openRematchOnClick = () => {
        if (selectedRowData === null) return;
        setRematchEntityId(selectedRowData.id)
        setOpenRematch(true)
    }

    const swapConceptEntity = () => {
        if (selectedRowData === null) return;
        let boundaryId = selectedRowData.id
        let sameEntity = selectedRowData.same_entity.toLowerCase() === 'yes'
        let entityName = selectedRowData.new_name
        setAlertDialogTitle(`Change to ${sameEntity? 'new':'existing'} entity concept`)
        setAlertDialogDescription(`Are you sure you want to set ${entityName} as ${sameEntity? 'new':'existing'} entity concept?`)
        setSwapBoundaryId(boundaryId)
    }

    const swapConceptEntityOnConfirmed = () => {
        setAlertDialogLoading(true)
        postData(
            `${SWAP_ENTITY_CONCEPT_URL}`, {
                'boundary_comparison_id': swapBoundaryId
            }
          ).then(
            () => {
                setAlertDialogLoading(false)
                fetchingComparisonData()
                setSwapBoundaryId(null)
            }
          ).catch(() => {
            setAlertDialogLoading(false)
            alert('Error calling API')
          })
    }

    const onRematchConfirmed = (rematchData: any) => {
        setOpenRematch(false)
        // refresh row data
        fetchingComparisonData()
        // refresh summary
        fetchSummary(rematchData.id)
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

    const handleFilterSubmit = (filterList: any) => {
        let _filter: any = {
            'search_text': filter.search_text
        }
        for (let idx in filterList) {
            let col = columns[idx]
            if (!col.options.filter)
                continue
            let column_name = col.name
            if (column_name.indexOf('similarity') >= 0 || column_name.indexOf('distance') >= 0) {
                // ensure both values are valid float
                if (filterList[idx].length < 2)
                    continue
                let _min = parseFloat(filterList[idx][0])
                let _max = parseFloat(filterList[idx][1])
                if (isNaN(_min) && isNaN(_max))
                    continue
                _filter[`min_${column_name}`] = isNaN(_min) ? 0 : _min
                _filter[`max_${column_name}`] = isNaN(_max) ? 0 : _max
            } else {
                if (filterList[idx] && filterList[idx].length)
                    _filter[column_name] = filterList[idx][0]
            }
        }
        setFilter(_filter)
    }

    const onRowSelected = (currentRowsSelected: any, allRowsSelected: any, rowsSelected: any) => {
        if (rowsSelected && rowsSelected.length) {
            setRowsSelected([...rowsSelected])
        }
    }

    const onPreviousRow = () => {
        let _selected_idx = rowsSelected[0]
        if (_selected_idx > 0) {
            _selected_idx--;
            setRowsSelected([_selected_idx])
        } else if (pagination.page > 0) {
            // navigate to prev page and set selection from bottom
            setInitSelection(1)
            setPagination({
                ...pagination,
                page: pagination.page - 1
            })
        }
    }

    const onNextRow = () => {
        let _selected_idx = rowsSelected[0]
        if (_selected_idx + 1 < data.length) {
            _selected_idx++;
            setRowsSelected([_selected_idx])
        } else if (pagination.page + 1 < totalPage) {
            // navigate to next page
            setInitSelection(0)
            setPagination({
                ...pagination,
                page: pagination.page + 1
            })
        }
    }

    return (
        <Scrollable>
         <Grid className={'detail-match'} container spacing={1} flexWrap='nowrap'>
            <Grid item xs={12} md={8} className={'detail-match-table'} ref={ref}
                sx={{flexGrow:{ sm: 1}}}>
                {!loading && <ResizeTableEvent containerRef={ref} onBeforeResize={() => setTableHeight(0)}
                    onResize={(clientHeight:number) => {
                        setTableHeight(clientHeight - TABLE_OFFSET_HEIGHT)
                    }} />}
                <AlertDialog open={swapBoundaryId !== null} alertLoading={alertDialogLoading} alertDialogTitle={alertDialogTitle}
                    alertDialogDescription={alertDialogDescription} alertConfirmed={() => swapConceptEntityOnConfirmed()}
                    alertClosed={() => setSwapBoundaryId(null)}
                />
                <MUIDataTable columns={columns} data={data}
                    title={<div>
                        <Select
                            disabled={fetchingSummary}
                            onChange={(event: SelectChangeEvent) => changeLevel(event.target.value)}
                            value={selectedLevel}
                            className={'level-select'}>
                            {props.uploadSession?.levels?.map((level) => {
                                return <MenuItem key={level}
                                                value={level}>Level {level}</MenuItem>
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
                        selectToolbarPlacement: 'none',
                        selectableRowsHideCheckboxes: true,
                        selectableRowsOnClick: true,
                        rowsSelected: rowsSelected,
                        onRowSelectionChange: onRowSelected,
                        expandableRows: false,
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
                        setRowProps: (rowData: any[], dataIndex: Number, rowIndex: Number) => {
                            const sameEntity = rowData[COLUMNS.indexOf('same_entity')]
                            const matchingLevel = rowData[COLUMNS.indexOf('matching_level')]
                            let className = 'DetailMatchRow'
                            if (sameEntity === 'No') {
                                className = className + ' NoComparison'
                            }
                            if (!checkMatchingLevel(matchingLevel, selectedLevel, loading)) {
                                className = className + ' WarningCell'
                            }
                            return {
                                className: className
                            }
                        },
                        onSearchChange: (searchText: string) => {
                            handleSearchOnChange(searchText)
                        },
                        searchText: filter.search_text,
                        searchOpen: (filter.search_text != null && filter.search_text.length > 0),
                        onFilterChange: (column, filterList, type) => {
                            handleFilterSubmit(filterList)
                        },
                        confirmFilters: true,
                        customFilterDialogFooter: (currentFilterList, applyNewFilters) => {
                            return (
                              <div style={{marginTop: '40px'}}>
                                <Button variant="contained" onClick={() => {
                                    let _filterList = applyNewFilters()
                                    handleFilterSubmit(_filterList)
                                }}>Apply Filters</Button>
                              </div>
                            );
                        },
                }}
                components={{
                    icons: {
                    FilterIcon
                    }
                }}/>
            </Grid>
            <Grid item xs={12} md={4} sx={{flexGrow:1}}>
                <Grid container flexDirection={'column'} sx={{height: '100%'}}>
                    <Grid item>
                        <Grid container flexDirection={'column'} sx={{height: '100%'}} className='CompactTableContainer'>
                            <Grid item container flexDirection={'row'} justifyContent={'space-between'} className='ButtonContainer'>
                                <Grid item><Button disabled={loading} onClick={onPreviousRow} variant='outlined' title='Select previous row (Shortcut: Arrow Key Up)'>Previous</Button></Grid>
                                <Grid item><Button disabled={loading} onClick={onNextRow} variant='outlined' title='Select next row (Shortcut: Arrow Key Down)'>Next</Button></Grid>
                                <Grid item><Button disabled={loading || isReadOnly || props.uploadSession.revisionNumber === 1} onClick={openRematchOnClick} variant='contained' title={isReadOnly ? 'The data has been approved': 'Rematch'}>Rematch</Button></Grid>
                                <Grid item><ConceptButton loading={loading || isReadOnly} onClick={swapConceptEntity} data={selectedRowData}  /></Grid>
                            </Grid>
                        </Grid>
                    </Grid>
                    <Grid item>
                        { loading ? <Skeleton variant='rectangular' height={'300px'} width={'100%'} /> : <MatchCompactTable selectedLevel={selectedLevel} data={selectedRowData} loading={loading} /> }
                    </Grid>
                    <Grid item flex={1} display={'flex'}>
                        { loading ? <Skeleton variant='rectangular' height={'100%'} width={'100%'} /> : 
                            <ReviewMap bbox={boundaryBbox}
                                mainBoundary={mainBoundary}
                                comparisonBoundary={comparisonBoundary}
                                selectedLevel={selectedLevel}
                                uploadSession={props.uploadSession}
                                mainBoundaryData={mainBoundaryData}
                                comparisonBoundaryData={comparisonBoundaryData}
                                />
                        }
                    </Grid>
                </Grid>
            </Grid>
            <Modal open={openRematch} onClose={() => setOpenRematch(false)} >
                <Box className="rematch-modal">
                    <h2>Rematch Boundary</h2>
                    <RematchEntityList handleOnBack={() => setOpenRematch(false)}
                        onRematchConfirmed={onRematchConfirmed} id={rematchEntityId}
                        entityUploadId={props.uploadSession.entityUploadId} />
                </Box>
            </Modal>
        </Grid>
    </Scrollable>
    )
}
