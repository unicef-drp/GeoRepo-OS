import React, {useEffect, useState} from "react";
import '../../styles/LayerUploadConfig.scss';
import {
    Button,
    Grid
} from "@mui/material";
import MUIDataTable from "mui-datatables";
import FilterAlt from '@mui/icons-material/FilterAlt';
import {fetchingData} from "../../utils/Requests";
import {LayerConfigInterface} from "./SaveLayerConfig";
import Loading from "../../components/Loading";

const FilterIcon: any = FilterAlt
const LIST_LAYER_CONFIG_URL = '/api/layer-config/list/'
const LOAD_LAYER_CONFIG_URL = '/api/layer-config/load/'

interface LayerLoadConfigInterface {
    level: string,
    attributes: string[],
    handleOnBack: Function,
    loadOnSuccess: Function
}

interface LayerConfigItemInterface {
    id: number,
    name: string,
    level: string,
    dataset_label: string,
    created_date: string,
    created_by: string
}

export default function LoadLayerConfig(props: LayerLoadConfigInterface) {
    const [loading, setLoading] = useState(true)
    const [configList, setConfigList] = useState<LayerConfigItemInterface[]>([])
    const [selectedRow, setSelectedRow] = useState(-1)
    const columns = [
        {
            name: 'name',
            label: 'Name'
        },
        {
            name: 'level',
            label: 'Level'
        },
        {
            name: 'dataset_label',
            label: 'Dataset'
        },
        {
            name: 'created_date',
            label: 'Created Date'
        },
        {
            name: 'created_by',
            label: 'Created By'
        }]

    useEffect(() => {
        // fetch config list
        fetchingData(LIST_LAYER_CONFIG_URL, {
            level : props.level
        },{}, null, false).then((data) => {
            setLoading(false)
            if (data.responseStatus == 'success') {
                setConfigList(data.responseData.map((x:LayerConfigItemInterface) => {
                    x.created_date = new Date(x.created_date).toDateString()
                    return x
                }))
            } else {
                console.error('Error fetching data')
            }
        })
    },[])

    const prepareLoadedConfig = (config: LayerConfigInterface): LayerConfigInterface => {
        // check the attribute in config exist in attribute list
        // if not exist, then set to empty to prevent saving the layer with incorrect value
        if (config.privacy_level_field) {
            if (props.attributes.filter((attrib) => config.privacy_level_field === attrib).length === 0)
                config.privacy_level_field = ''
        }
        if (config.location_type_field) {
            if (props.attributes.filter((attrib) => config.location_type_field === attrib).length === 0)
                config.location_type_field = ''
        }
        if (config.parent_id_field) {
            if (props.attributes.filter((attrib) => config.parent_id_field === attrib).length === 0)
                config.parent_id_field = ''
        }
        if (config.source_field) {
            if (props.attributes.filter((attrib) => config.source_field === attrib).length === 0)
                config.source_field = ''
        }
        for (let name_field of config.name_fields) {
            if (props.attributes.filter((attrib) => name_field.field === attrib).length === 0)
                name_field.field = ''
            if (typeof name_field.selectedLanguage === 'undefined')
                name_field.selectedLanguage = ''
            if (typeof name_field.label === 'undefined')
                name_field.label = ''
        }
        for (let id_field of config.id_fields) {
            if (props.attributes.filter((attrib) => id_field.field === attrib).length === 0)
                id_field.field = ''
        }
        if (config.boundary_type) {
            if (props.attributes.filter((attrib) => config.boundary_type === attrib).length === 0)
                config.boundary_type = ''
        }
        return config
    }

    const onLoadClick = () => {
        setLoading(true)
        fetchingData(LOAD_LAYER_CONFIG_URL, {
            id : configList[selectedRow].id
        }, {}).then((data) => {
            setLoading(false)
            if (data.responseStatus == 'success') {
                props.loadOnSuccess(prepareLoadedConfig(data.responseData))
            } else {
                console.error('Error fetching data layer config!')
            }
        })
    }

    const onCancelClick = () => {
        props.handleOnBack();
    }

    const onRowSelected = (rowsSelected: any) => {
        setSelectedRow(rowsSelected[0].dataIndex)
    }

    return (
        loading ? <div style={{ height: 300, display: "flex", alignItems: "center", justifyContent: "center" }}><Loading/></div> :
        <div className="load-layer-config-container">
            <MUIDataTable
                    title={''}
                    data={configList}
                    columns={columns}
                    options={{
                        selectableRows: 'single',
                        selectableRowsHeader: false,
                        selectableRowsHideCheckboxes: true,
                        selectableRowsOnClick: true,
                        selectToolbarPlacement: 'none',
                        onRowSelectionChange: onRowSelected,
                        download: false,
                        print: false,
                        tableBodyMaxHeight: '400px'
                    }}
                    components={{
                       icons: {
                         FilterIcon
                       }
                     }}
            />
            <div className="load-button-container">
                <Grid container direction="row" 
                    justifyContent="flex-end" 
                    alignItems="center"
                    spacing={2}>
                    <Grid item>
                        <Button disabled={selectedRow === -1} onClick={onLoadClick} variant="contained">
                            Load Config
                        </Button>
                    </Grid>
                    <Grid item>
                        <Button onClick={onCancelClick} variant="outlined">
                            Cancel
                        </Button>
                    </Grid>
              </Grid>
            </div>
        </div>
      )
}