import React, {Fragment, MouseEventHandler, useEffect, useState, useRef} from 'react';

import {GridActionsCellItem, GridSortingInitialState} from "@mui/x-data-grid"
import IconButton from '@mui/material/IconButton';
import DeleteIcon from "@mui/icons-material/Delete";
import AddIcon from "@mui/icons-material/Add";
import EditIcon from "@mui/icons-material/Edit";
import MoreVertIcon from '@mui/icons-material/MoreVert';
import {useNavigate} from "react-router-dom";

import {AdminTable, ExpandedRowInterface, RowData} from './Table';
import MoreAction from "./Elements/MoreAction";
import {fetchingData} from "../utils/Requests";

import '../styles/List.scss';
import axios from "axios";
import {capitalize} from "../utils/Helpers";
import {Button, ButtonGroup} from "@mui/material";
import {MUIDataTableColumnDef} from "mui-datatables";
import ResizeTableEvent from "./ResizeTableEvent"

// 145 = filter + filter chips + col headers
export const TABLE_OFFSET_HEIGHT = 130

axios.defaults.headers.common = {
    'X-CSRFToken' : (window as any).csrfToken
}

export interface ActionDataInterface {
    field: string,
    name: string,
    icon?: JSX.Element,
    url?: string,
    color?: "inherit" | "error" | "success" | "info" | "warning" | "primary" | "secondary",
    onClick?: (data: any, event?: React.MouseEvent<HTMLButtonElement>) => void,
    isDisabled?: (data: any) => boolean,
    actionGroup?: string,
    getName?: (data: any) => string,
    className?: string
}

interface ListInterface {
    pageName: string,
    listUrl: string,
    initData: RowData[],
    selectionChanged: null | ((data: any) => void),
    sortingDefault?: null | GridSortingInitialState,
    addUrl?: string,
    redirectUrl?: string,
    editUrl?: string,
    onEditClick?: any,
    detailUrl?: string,
    actionData?: ActionDataInterface[],
    isRowSelectable?: boolean,
    expandableRow?: null | ((props: ExpandedRowInterface) => JSX.Element | JSX.Element[]),
    onRowClick?: (rowData: string[], rowMeta: { dataIndex: number, rowIndex: number }) => void,
    options?: any,
    customRowRender?: any,
    customOptions?: any,
    customColumnHeaderRender?: any,
    canRowBeSelected?: (dataIndex: number, rowData: any) => boolean,
    excludedColumns?: string[],
    title?: React.ReactNode,
    fetchUseCache?: boolean
}

/**
 *
 * DEFAULT COLUMNS ACTIONS
 * @param {Array} rowData Params for action.
 * @param addUrl
 * @param {String} redirectUrl Url for redirecting after action done.
 * @param {String} editUrl Url for edit row.
 * @param onEditClick
 * @param {String} detailUrl Url for detail of row.
 * @param {function} navigate A function to navigate to other view.
 * @param {React.Component} moreActions More actions before delete
 * @returns {list}
 */
export function COLUMNS_ACTION(
    rowData: string[],
    addUrl?: string,
    redirectUrl?: string,
    editUrl?: string,
    onEditClick?: any,
    detailUrl?: string,
    navigate?: any,
    moreActions?: React.Component,
) {
    const actions = []
    const rowId = rowData[0]
    const rowName = rowData[1]

    actions.push(
        <GridActionsCellItem
            icon={
                <MoreAction moreIcon={<MoreVertIcon/>}>
                    {
                        addUrl ? <div onClick={() => {
                            const postData = {
                                id: rowId
                            }
                            axios.post(addUrl, postData).then(
                              response => {
                                  const data = response.data
                                  if (data.redirect_url) {
                                      navigate(data.redirect_url)
                                  }
                              }
                            ).catch(error => alert('Error adding new data.'))
                        }}><AddIcon/> Add</div> : ''
                    }
                    {
                        editUrl || onEditClick ? <div onClick={
                            () => onEditClick ? onEditClick(rowData) : navigate(editUrl + '?id=' + rowId)
                        }>
                            <EditIcon/> Edit
                        </div> : ''
                    }
                    {
                        moreActions ? React.Children.map(moreActions, child => {
                            return child
                        }) : ''
                    }
                    {
                        detailUrl ?
                            <div className='error' onClick={
                                () => {
                                    const api = detailUrl.replace('/0', `/${rowId}`);
                                    if (confirm(`Are you sure you want to delete : ${rowData[1] ? rowName : rowId}?`)) {
                                        // todo : change to fetch or axios
                                        // $.ajax({
                                        //     url: api,
                                        //     method: 'DELETE',
                                        //     success: function () {
                                        //         window.location.href = redirectUrl;
                                        //     },
                                        //     beforeSend: beforeAjaxSend
                                        // });
                                        return false;
                                    }
                                }
                            }>
                                <DeleteIcon/> Delete
                            </div> : null
                    }
                </MoreAction>
            }
            label="More"
        />
    )
    return actions
}

/**
 * Admin List App
 * @param {String} pageName Page Name.
 * @param {String} listUrl Url for list row.
 * @param {list} initData Init Data.
 * @param {function} selectionChanged Function when selection changed.
 * @param {GridSortingInitialState} sortingDefault
 * @param {String} addUrl
 * @param {String} redirectUrl
 * @param {String} editUrl
 * @param onEditClick
 * @param {String} detailUrl
 * @param {ActionDataInterface[]} actionData
 * @param {boolean} isRowSelectable
 * @param {(props: ExpandedRowInterface) => Element} expandableRow
 */
export default function List(
    {
        pageName,
        listUrl,
        initData,
        selectionChanged,
        sortingDefault = null,
        addUrl = '',
        redirectUrl = '',
        editUrl = '',
        onEditClick = null,
        detailUrl = '',
        actionData = [],
        isRowSelectable = false,
        expandableRow = null,
        onRowClick = null,
        options = {},
        customRowRender = {},
        customColumnHeaderRender = {},
        customOptions = {},
        canRowBeSelected = null,
        excludedColumns = [],
        title = null,
        fetchUseCache = true
    } : ListInterface
) {
    const [data, setData] = useState(initData);
    const [tableColumns, setTableColumns] = useState<MUIDataTableColumnDef[]>([])
    const [search, setSearch] = useState(null);
    const navigate = useNavigate()
    const ref = useRef(null)
    const [tableHeight, setTableHeight] = useState(0)
    const [rowsPerPage, setRowsPerPage] = useState(options['rowsPerPage'] || 50)

    /** Fetch list of data */
    const fetchData = (url: string) => {
        if (!data || data.length == 0) {
            fetchingData(url, {}, {}, null, fetchUseCache).then(
                (data) => {
                    if (data.responseStatus == 'success') {
                        setData(data.responseData)
                    } else if (data.responseStatusCode === 403) {
                        navigate('/invalid_permission')
                    } else {
                        console.error('Error fetching data')
                    }
                    return
                }
            )
        }
    }

    useEffect(() => {
        setData(initData)
    }, [initData])

    useEffect(() => {
        if (data.length > 0 && tableColumns.length === 0) {
            const _columns:MUIDataTableColumnDef[] = []
            for (const rowKey of Object.keys(data[0])) {
                const rowName = rowKey.replace(/_/gi, ' ')
                let isAction = false
                for (const _actionData of actionData) {
                    if (rowKey === _actionData.field) {
                        isAction = true
                        break
                    }
                }

                if (!isAction) {
                    let _column:MUIDataTableColumnDef = {
                        name: rowKey,
                        label: capitalize(rowName),
                    }
                    if (customRowRender[rowKey] !== undefined) {
                        // using custom body render
                        _column['options'] = {
                            filter: false,
                            sort: false,
                            display: rowKey !== 'id',
                            customBodyRender: customRowRender[rowKey]
                        }
                    } else {
                        _column['options'] = {
                            display: rowKey !== 'id' && excludedColumns.findIndex((col_name) => col_name === rowKey) === -1
                        }
                    }
                    if (customColumnHeaderRender[rowKey] !== undefined) {
                        _column['options'] = {
                            customHeadLabelRender: customColumnHeaderRender[rowKey]
                        }
                    }
                    if (customOptions[rowKey] !== undefined) {
                        _column['options'] = customOptions[rowKey]
                    }
                    if (rowKey.toLowerCase().includes('date')) {
                        _column['options'] = {
                            filter: false,
                            customBodyRender: (value, tableMeta, updateValue) => {
                                if (value.includes('T') && value.includes('Z')) {
                                    return new Date(value).toDateString()
                                }
                                return value
                            }
                        }
                    }
                    _columns.push(_column)
                }
            }

            if (actionData) {
                    _columns.push({
                        name: '',
                        options: {
                            customBodyRender: (value: any, tableMeta: any, updateValue: any) => {
                                const rowData: any = data.find(({id}) => id === tableMeta.rowData[0])
                                if (!rowData) return null
                                // grouping the action data buttons
                                // e.g. Edit and Delete might be better to separate it into different group
                                let actionDataGroup:any = {
                                    'default': []
                                }
                                let iconActionGroup:JSX.Element[] = []
                                actionData.map((_actionData, idx) => {
                                    let element = null
                                    if (_actionData.onClick) {
                                        if (_actionData.icon) {
                                            // use icon button
                                            element = (
                                                <IconButton aria-label={_actionData.getName ? _actionData.getName(rowData) : _actionData.name}
                                                    title={_actionData.getName ? _actionData.getName(rowData) : _actionData.name}
                                                    key={idx}
                                                    disabled={_actionData.isDisabled ? _actionData.isDisabled(rowData) : false}
                                                    color={_actionData.color ? _actionData.color : 'primary'}
                                                    onClick={(e) => {
                                                        e.stopPropagation();
                                                        _actionData.onClick(rowData, e)
                                                    }}
                                                    className={_actionData.className ? _actionData.className : ''}
                                                >
                                                    {_actionData.icon}
                                                </IconButton>
                                            )
                                        } else {
                                            element = (
                                                <Button
                                                    key={idx}
                                                    color={_actionData.color ? _actionData.color : 'primary'}
                                                    disabled={_actionData.isDisabled ? _actionData.isDisabled(rowData) : false}
                                                    onClick={(e) => {
                                                        e.stopPropagation();
                                                        _actionData.onClick(rowData, e)
                                                    }} variant={'contained'}
                                                    className={_actionData.className ? _actionData.className : ''}
                                                    sx={{minWidth: '82px'}}>{_actionData.getName ? _actionData.getName(rowData) : _actionData.name}
                                                </Button>
                                            )
                                        }
                                    } else if (rowData[_actionData.field]) {
                                        if (_actionData.icon) {
                                            // use icon button
                                            element = (
                                                <IconButton aria-label="Edit"
                                                    title="Edit"
                                                    key={idx}
                                                    disabled={_actionData.isDisabled ? _actionData.isDisabled(rowData) : false}
                                                    color={_actionData.color ? _actionData.color : 'primary'}
                                                    className={_actionData.className ? _actionData.className : ''}
                                                    onClick={(e) => navigate(_actionData.url + rowData[_actionData.field])}
                                                >
                                                    {_actionData.icon}
                                                </IconButton>
                                            )
                                        } else {
                                            element = (
                                                <Button
                                                    key={idx}
                                                    disabled={_actionData.isDisabled ? _actionData.isDisabled(rowData) : false}
                                                    onClick={(e) => navigate(_actionData.url + rowData[_actionData.field])}
                                                    variant={'contained'}
                                                    className={_actionData.className ? _actionData.className : ''}
                                                    sx={{minWidth: '82px'}}>Edit
                                                </Button>
                                            )
                                        }
                                    }
                                    if (_actionData.icon) {
                                        // add to icon actions group
                                        iconActionGroup.push(element)
                                    } else if (_actionData.actionGroup) {
                                        if (actionDataGroup[_actionData.actionGroup] === undefined) {
                                            actionDataGroup[_actionData.actionGroup] = []
                                        }
                                        actionDataGroup[_actionData.actionGroup].push(element)
                                    } else {
                                        actionDataGroup['default'].push(element)
                                    }
                                })
                                // check whether this is icon actions or button groups
                                if (iconActionGroup.length > 0) {
                                    return (
                                        <div className="TableActionContent">
                                            {
                                                iconActionGroup.map((_action_button:any, idx:any) => _action_button)
                                            }
                                        </div>
                                    )
                                }
                                return (
                                    <div className="TableActionContent">
                                        {
                                            Object.entries(actionDataGroup).map((_action_group:any, idx:any) => 
                                                <ButtonGroup variant="contained" key={_action_group[0]} sx={{ ...(idx > 0 && {marginLeft: '10px'})}} >
                                                    {
                                                        _action_group[1].map((_action_button:any, idx_element:number) => _action_button)
                                                    }
                                                </ButtonGroup>
                                            )
                                        }
                                    </div>
                                )
                            }
                        },
                    })
                }

            // Add action to column
            if (editUrl || detailUrl || redirectUrl || onEditClick) {
                _columns.push({
                    name: '',
                    options: {
                        customBodyRender: (value: any, tableMeta: any, updateValue: any) => {
                            const rowData = tableMeta.rowData
                            return COLUMNS_ACTION(
                              rowData, addUrl, redirectUrl, editUrl, onEditClick, detailUrl, navigate)
                        }
                    }
                })
            }
            setTableColumns(_columns)
        }
    }, [data])

    // Show modal when url changed
    useEffect(() => {
        if (listUrl) {
            fetchData(listUrl)
        }
    }, [])

    /** Search on change */
    const searchOnChange = (evt: any) => {
        setSearch(evt.target.value.toLowerCase())
    }

    /** Filter by search input */
    let rows = data;
    if (search) {
        rows = rows.filter(row => {
            let found = false;
            for (const rowKey of Object.keys(row)) {
                // @ts-ignore
                found = (row[rowKey] + '').toLowerCase().includes(search)
                if (found) {
                    return found
                }
            }
            return found;
        })
    }

    /** Rows per page change **/
    const onRowsPerPageChange = (numberOfRowsPerPage: number) => {
        setRowsPerPage(numberOfRowsPerPage)
    }

    /** Render **/
    return (
        <Fragment>
            <div className='AdminList' ref={ref}>
                <ResizeTableEvent containerRef={ref} onBeforeResize={() => setTableHeight(0)}
                    onResize={(clientHeight:number) => setTableHeight(clientHeight - TABLE_OFFSET_HEIGHT)} />
                <AdminTable
                    title={title}
                    name={pageName}
                    rows={rows}
                    columns={tableColumns}
                    selectionChanged={selectionChanged}
                    isRowSelectable={isRowSelectable}
                    sortingDefault={sortingDefault}
                    onRowClick={onRowClick}
                    ExpandableRow={expandableRow}
                    canRowBeSelected={canRowBeSelected}
                    onRowsPerPageChange={onRowsPerPageChange}
                    options={{
                        ...options,
                        ...(options['tableBodyMaxHeight'] === undefined && {'tableBodyMaxHeight': `${tableHeight}px`}),
                        ...{'rowsPerPage': rowsPerPage}
                    }}
                />
            </div>
        </Fragment>
    );
}
