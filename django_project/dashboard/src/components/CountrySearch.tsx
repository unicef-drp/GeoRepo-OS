import React, {useState, useMemo} from 'react';
import axios from 'axios';
import Autocomplete from '@mui/material/Autocomplete';
import Checkbox from '@mui/material/Checkbox';
import TextField from '@mui/material/TextField';
import CheckBoxOutlineBlankIcon from '@mui/icons-material/CheckBoxOutlineBlank';
import CheckBoxIcon from '@mui/icons-material/CheckBox';
import { debounce } from '@mui/material/utils';

const checkBoxOutlinedicon = <CheckBoxOutlineBlankIcon fontSize="small" />;
const checkBoxCheckedIcon = <CheckBoxIcon fontSize="small" />;
const SEARCH_API_URL = '/api/entity/country/'

interface CountrySearchInterface {
    objectType: string;
    objectId: number;
    filterList: any;
    onChange: any;
    index: any;
    column: any;
}

export default function CountrySearch(props: CountrySearchInterface) {
    const [value, setValue] = useState<String | null>(null)
    const [inputValue, setInputValue] = useState('')
    const [options, setOptions] = useState<String[]>([])
    const loaded = React.useRef(false)

    const doSearchCountry = useMemo(
        () =>
            debounce(
                (
                    request: {input: string},
                    callback: (results?: String[]) => void,
                ) => {
                    let _url = `${SEARCH_API_URL}${props.objectType}/search/?search_text=${request.input}`
                    if (props.objectType === 'dataset') {
                        _url = _url + `&dataset_id=${props.objectId}`
                    } else if (props.objectType === 'view') {
                        _url = _url + `&view_id=${props.objectId}`
                    } else if (props.objectType === 'upload_session') {
                        _url = _url + `&session_id=${props.objectId}`
                    }
                    axios.get(_url).then(
                        response => {
                            let _results = response.data['countries'] as String[]
                            callback(_results)
                        }
                    ).catch((error) => {
                        console.log('Failed to search country ', error)
                        callback([])
                    })
                },
                400
            ),
        [],
    )

    return (
        <div>
            <Autocomplete
                multiple
                id={`checkboxes-id-filter-country`}
                options={options}
                disableCloseOnSelect
                value={props.filterList[props.index]}
                filterOptions={(x) => x}
                onChange={(event: any, newValue: any | null) => {
                    props.filterList[props.index] = newValue
                    props.onChange(props.filterList[props.index], props.index, props.column)
                }}
                getOptionLabel={(option: string) => `${option}`}
                renderOption={(props, option, { selected }) => (
                    <li {...props}>
                    <Checkbox
                        icon={checkBoxOutlinedicon}
                        checkedIcon={checkBoxCheckedIcon}
                        style={{ marginRight: 8 }}
                        checked={selected}
                    />
                    {option}
                    </li>
                )}
                renderInput={(params) => (
                    <TextField {...params} label={'Country'} variant="standard" />
                )}
            />
        </div>
    )

}
