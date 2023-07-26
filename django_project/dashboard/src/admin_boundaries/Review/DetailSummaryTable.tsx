import React, {useEffect, useState, useRef} from 'react';
import MUIDataTable from "mui-datatables";
import FilterAlt from '@mui/icons-material/FilterAlt';
import {useSearchParams} from "react-router-dom";
import Grid from "@mui/material/Grid";
import ResizeTableEvent from "../../components/ResizeTableEvent"
import {TABLE_OFFSET_HEIGHT} from '../../components/List'
import ColumnHeaderIcon from '../../components/ColumnHeaderIcon'
import axios from "axios";
import Scrollable from '../../components/Scrollable';
import { ReviewTabInterface } from '../../models/upload';

const COLUMNS = [
    'id',
    'level',
    'new_count',
    'previous_count',
    'new_total_area',
    'previous_total_area',
    'matching_count',
    'avg_similarity_new',
    'avg_similarity_matching'
]
export interface DetailSummaryData {
    id: string,
    level: string,
    new_count: number,
    previous_count: number,
    new_total_area: number,
    previous_total_area: number,
    matching_count: number,
    avg_similarity_new: number,
    avg_similarity_matching: number
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
                    let _data: DetailSummaryData[] = []
                    for (let _item of response.data) {
                        _data.push({
                            'id': _item['id'],
                            'level': _item['level'],
                            'new_count': _item['new_count'],
                            'previous_count': _item['old_count'],
                            'new_total_area': _item['new_total_area'],
                            'previous_total_area': _item['old_total_area'],
                            'matching_count': _item['matching_count'],
                            'avg_similarity_new': 100 * _item['avg_similarity_new'],
                            'avg_similarity_matching': 100 * _item['avg_similarity_old']
                        })
                    }
                    setSummaryData(_data)
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
            if (column_name === 'avg_similarity_new') {
                _options['label'] = 'Avg similarity (% new)'
                _options['options']['customHeadLabelRender'] = (columnMeta: any, handleToggleColumn: Function) => {
                    return <ColumnHeaderIcon title='Avg similarity (% new)' tooltipTitle='Average Geometry Similarity (% new)'
                        tooltipDescription={<p>The percentage of the new boundary area covered by the matching boundary</p>}
                    />
                }
            } else if (column_name === 'avg_similarity_matching') {
                _options['label'] = 'Avg similarity (% match)'
                _options['options']['customHeadLabelRender'] = (columnMeta: any, handleToggleColumn: Function) => {
                    return <ColumnHeaderIcon title='Avg similarity (% match)' tooltipTitle='Average Geometry Similarity (% match)'
                        tooltipDescription={<p>The percentage of the matching boundary area covered by the new boundary</p>}
                    />
                }
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