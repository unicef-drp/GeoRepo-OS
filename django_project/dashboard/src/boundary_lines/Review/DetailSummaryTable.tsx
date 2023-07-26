import React, {useEffect, useState, useRef} from 'react';
import MUIDataTable from "mui-datatables";
import FilterAlt from '@mui/icons-material/FilterAlt';
import {useSearchParams} from "react-router-dom";
import Grid from "@mui/material/Grid";
import ResizeTableEvent from "../../components/ResizeTableEvent"
import {TABLE_OFFSET_HEIGHT} from '../../components/List'
import axios from "axios";
import Scrollable from '../../components/Scrollable';
import { ReviewTabInterface } from '../../models/upload';

const COLUMNS = [
    'boundary_type',
    'boundary_type_label',
    'count',
]
export interface DetailSummaryData {
    boundary_type: string,
    boundary_type_label: string,
    count: number
}
const FilterIcon: any = FilterAlt
const BOUNDARY_COMPARISON_URL = '/api/boundary-comparison-summary/'

export default function DetailSummaryTable(props: ReviewTabInterface) {
    const [columns, setColumns] = useState<any>([])
    const ref = useRef(null)
    const [tableHeight, setTableHeight] = useState(0)
    const [tableForceUpdate, setTableForceUpdate] = useState(null)
    const [searchParams, setSearchParams] = useSearchParams()
    const [summaryData, setSummaryData] = useState<DetailSummaryData[]>([])
    
    useEffect(() => {
        if (summaryData) {
            setTableForceUpdate(new Date())
        }
    }, [summaryData])

    useEffect(() => {
        fetchSummaryData()
    }, [props.updated_date])
    
    const fetchSummaryData = () => {
        axios.get(BOUNDARY_COMPARISON_URL + searchParams.get('id')).then(
            response => {
                if (response.data) {
                    setSummaryData(response.data as DetailSummaryData[])
                }
            }, error => {
                console.log(error)
            }
        )
    }

    useEffect(() => {
        setColumns(COLUMNS.map((column_name) => {
            let _options:any = {
                name: column_name,
                label: column_name.charAt(0).toUpperCase() + column_name.slice(1).replaceAll('_', ' '),
                options: {
                    display: column_name !== 'id'
                }
            }
            // override header name for similarity columns
            if (column_name === 'boundary_type_label') {
                _options['label'] = 'Label'
            } else if (column_name === 'count') {
                _options['label'] = 'Number of lines'
            }
            return _options
        }))
    }, [])

    return (
        <Scrollable>
            <Grid container flexDirection='column' style={{height:'100%'}}>
                <Grid item style={{height:'100%', display: 'flex', width: '100%'}} ref={ref} className='DetailSummaryTable'>
                    <ResizeTableEvent containerRef={ref} onBeforeResize={() => setTableHeight(0)}
                        onResize={(clientHeight:number) => {
                            setTableHeight(clientHeight - TABLE_OFFSET_HEIGHT - 40)
                        }} forceUpdate={tableForceUpdate} />
                    <MUIDataTable columns={columns} data={summaryData} title={''}
                            options={{
                                selectableRows: 'none',
                                textLabels: {
                                    body: {
                                        noMatch: !props.uploadSession.comparisonReady ?
                                        (props.uploadSession.progress ? props.uploadSession.progress : 'Data is still being processed...') :
                                            'Sorry, there is no matching data to display',
                                    },
                                },
                                setTableProps: () => ({className: 'review-summary-table'}),
                                fixedHeader: true,
                                tableBodyHeight: `${tableHeight}px`,
                                tableBodyMaxHeight: `${tableHeight}px`,
                            }}
                            components={{
                                icons: {
                                    FilterIcon
                                }
                            }}
                    />
                </Grid>
            </Grid>
        </Scrollable>
    )
}