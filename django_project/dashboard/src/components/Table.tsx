import React, {useEffect, useState} from 'react';
import {GridSortingInitialState} from "@mui/x-data-grid";
import MUIDataTable, {MUIDataTableColumnDef} from "mui-datatables";
import FilterAlt from '@mui/icons-material/FilterAlt';

import '../styles/Table.scss';


const FilterIcon: any = FilterAlt

export interface RowData {
    id?: number,
    name?: string,
    category?: string,
    description?: string,
    shortcode?: string
}

interface AdminTableInterface {
    name: string,
    rows: RowData[],
    columns: MUIDataTableColumnDef[],
    selectionChanged: null | (([]) => void),
    sortingDefault: null | GridSortingInitialState,
    isRowSelectable?: boolean,
    ExpandableRow?: null | ((props: ExpandedRowInterface) => JSX.Element | JSX.Element[]),
    onRowClick?: (rowData: string[], rowMeta: { dataIndex: number, rowIndex: number }) => void,
    canRowBeSelected?: (dataIndex: number, rowData: any) => boolean,
    onRowsPerPageChange?: (numberOfRowsPerPage: number) => void,
    options?: any,
    title?: React.ReactNode
}

export interface ExpandedRowInterface {
  rowData: string[],
  rowMeta: {
    dataIndex: number,
    rowIndex: number
  }
}


/**
 * Admin Table
 * @param {string} name of the table
 * @param {Array} rows List of data.
 * @param {MUIDataTableColumnDef[]} columns Columns for the table.
 * @param {function} selectionChanged Function when selection changed.
 * @param {Object} sortingDefault Sorting default.
 * @param {boolean} isRowSelectable Indicate if all rows can be selected
 * @param {(any) => void} onRowClick Callback function that triggers when a row is clicked
 * @param {(props: ExpandedRowInterface) => Element} ExpandableRow Element inside expandable
 * @param options
 */
export function AdminTable({
                               name,
                               rows,
                               columns,
                               selectionChanged = null,
                               sortingDefault = null,
                               isRowSelectable = true,
                               onRowClick = null,
                               ExpandableRow = null,
                               canRowBeSelected = null,
                               onRowsPerPageChange = null,
                               options = {},
                               title = null
                           }: AdminTableInterface) {

    if (rows.length > 0 && columns.length > 0) {
        let selectableRowsMode = 'none'
        if (isRowSelectable) {
          if (options['selectableRows'] !== undefined)
            selectableRowsMode = options['selectableRows']
          else
            selectableRowsMode = 'multiple'
        }
        let rowsPerPage = options['rowsPerPage'] !== undefined ? options['rowsPerPage'] : 50
        let rowsPerPageOptions = options['rowsPerPageOptions'] !== undefined ? options['rowsPerPageOptions'] : [50, 100, 200]
        return (
          <div className='AdminTable'>
                <MUIDataTable
                    title={title ? title : ''}
                    data={rows}
                    columns={columns}
                    options={{
                      ...options,
                      onRowClick: onRowClick ? onRowClick : null,
                      onRowSelectionChange: (currentRowsSelected, allRowsSelected, rowsSelected) => {
                        // @ts-ignore
                        const rowDataSelected = rowsSelected.map((index) => rows[index]['id'])
                        if (selectionChanged) {
                          selectionChanged(rowDataSelected)
                        }
                      },
                      isRowSelectable: (dataIndex: number, selectedRows: any) => {
                        if (canRowBeSelected) {
                          return canRowBeSelected(dataIndex, rows[dataIndex])
                        }
                        return selectableRowsMode !== 'none'
                      },
                      selectableRows: selectableRowsMode,
                      rowsPerPage: rowsPerPage,
                      rowsPerPageOptions: rowsPerPageOptions,
                      isRowExpandable: (dataIndex, expandedRows) => {
                        return true
                      },
                      expandableRows: !!ExpandableRow,
                      expandableRowsHeader: false,
                      expandableRowsOnClick: true,
                      onTableChange: (action:string, tableState:any) => {
                        switch (action) {
                          case 'changeRowsPerPage':
                            if (onRowsPerPageChange) {
                              onRowsPerPageChange(tableState.rowsPerPage)
                            }
                            break;
                          default:
                        }
                      },
                      renderExpandableRow: (rowData, rowMeta) =>
                        // @ts-ignore
                        <ExpandableRow rowData={rowData} rowMeta={rowMeta}/>
                    }}
                    components={{
                      icons: {
                        FilterIcon
                      }
                    }}
                />
            </div>)
    } else {
        return <div className='AdminTable-Loading'>No data</div>
    }
}
