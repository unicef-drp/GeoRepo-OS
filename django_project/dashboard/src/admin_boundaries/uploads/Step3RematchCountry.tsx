import React, {useEffect, useState} from "react";

import axios from "axios";
import List from "../../components/List";
import Loading from "../../components/Loading";
import ColumnHeaderIcon from '../../components/ColumnHeaderIcon'

const LOAD_COUNTRY_LIST_URL = '/api/entity-upload-level1-list/'
const LOAD_REMATCH_LIST_URL = '/api/entity-upload-rematch-list/'
const REMATCH_UPLOAD_URL = '/api/entity-upload-rematch/'

export interface RematchCountryListInterface {
    entityUploadId: number,
    handleOnBack: Function
}

export default function Step3RematchCountryList(props: RematchCountryListInterface) {
    const [loading, setLoading] = useState(true)
    const [data, setData] = useState<any[]>([])

    const fetchCountryList = () => {
        axios.get(LOAD_COUNTRY_LIST_URL + `?id=${props.entityUploadId}`).then(
            response => {
                setLoading(false)
                if (response.data) {
                    setData(response.data)
                }
            }, error => {
                setLoading(false)
                console.log(error)
            }
        )
    }

    useEffect(() => {
        fetchCountryList()
    }, [props.entityUploadId])
    
    const onRowSelected = (rowsSelected: any) => {

    }

    const onCancelClick = () => {
        props.handleOnBack();
    }


    const customColumnHeaderRender = {
        'is_rematched': (columnMeta: any, handleToggleColumn: Function) => {
            return (
                <ColumnHeaderIcon title='Is Rematched' tooltipTitle='Is Rematched'
                            tooltipDescription={<p>True if the new parent default code is different from parent code in the layer file</p>}
                        />
            )
        },
        'overlap': (columnMeta: any, handleToggleColumn: Function) => {
            return (
                <ColumnHeaderIcon title='Overlap' tooltipTitle='Overlap'
                            tooltipDescription={
                                <p>
                                    The percentage of the geometry area covered by the parent geometry
                                </p>
                            }
                        />
            )
        }
    }

    return (
        loading ? <div style={{ height: 300, display: "flex", alignItems: "center", justifyContent: "center" }}><Loading/></div> :
        <div>
            <List
                pageName='Admin Level 1 List'
                listUrl={''}
                initData={data}
                selectionChanged={onRowSelected}
                isRowSelectable={false}
                options={{
                    sort: false,
                    filter: false,
                    download: false,
                    print: false,
                    tableBodyMaxHeight: '400px',
                    rowsPerPageOptions: [5, 10],
                    rowsPerPage: 10
                }}
                customColumnHeaderRender={customColumnHeaderRender}
            />
        </div>
    )
}