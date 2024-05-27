import React, {useEffect, useState} from 'react';
import { FormControlLabel, Checkbox } from '@mui/material';


interface SelectAllCheckboxInterface {
    totalSelected: number;
    totalItems: number;
    onSelectAll: () => void;
    onClear: () => void;
}

export default function SelectAllCheckbox(props: SelectAllCheckboxInterface) {
    const [label, setLabel] = useState('Select All')

    useEffect(() => {
        let _label = 'Select All'
        if (props.totalSelected > 0) {
            _label = `${props.totalSelected} selected`
        }
        setLabel(_label)
    }, [props.totalSelected, props.totalItems])

    const handleChange = () => {
        if (props.totalSelected === 0) {
            props.onSelectAll()
        } else {
            props.onClear()
        }
    }

    return (
        <FormControlLabel
            label={label}
            control={
                <Checkbox
                    checked={props.totalSelected > 0 && props.totalSelected === props.totalItems}
                    indeterminate={props.totalSelected > 0 && props.totalSelected < props.totalItems}
                    onChange={handleChange}
                />
            }
        />
    )
}

