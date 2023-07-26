import React, {useEffect, useState} from "react";
import Modal from "@mui/material/Modal";
import Box from "@mui/material/Box";
import Grid from "@mui/material/Grid";
import Typography from "@mui/material/Typography";
import TextField from "@mui/material/TextField";
import Button from "@mui/material/Button";
import {IdType} from "../../models/upload";
import {postData} from "../../utils/Requests";


const ADD_ID_TYPE_URL = '/api/id-type/add/'

export interface NewIdTypeInterface {
    id: string,
    name: string
}
  
interface AddIdTypeInterface {
    open: boolean,
    initialIdType: NewIdTypeInterface,
    onClosed: () => void,
    onSubmitted: (newIdType: NewIdTypeInterface, idType: IdType) => void
}

export default function AddIdType(props: AddIdTypeInterface) {
    const [loading, setLoading] = useState<boolean>(false)
    const [newIdType, setNewIdType] = useState<NewIdTypeInterface>(props.initialIdType)

    useEffect(() => {
        setNewIdType(props.initialIdType)
    }, [props.initialIdType])

    const addIdTypeOnClose = () => {
        setNewIdType(null)
        props.onClosed()
    }

    const addIdTypeOnSubmit = () => {
        if (newIdType === null || newIdType.name === '') {
            alert('Id Type value must not be empty!')
            return;
        }
        setLoading(true)
        postData(ADD_ID_TYPE_URL, newIdType).then(response => {
            setLoading(false)
            props.onSubmitted(newIdType, response.data)
        }).catch(error => {
            setLoading(false)
            error.response ? alert(error.response.data) :
                    alert('Unable to add new Id Type!')
        })
    }

    return (
        <Modal open={props.open} onClose={props.onClosed}>
            <Box className="layer-config-modal add-id-type">
                <div className="id-type-form">
                    <Grid container columnSpacing={1}>
                        <Grid className={'form-label'} item md={4} xl={4} xs={12}>
                            <Grid container direction="column" justifyContent="center" sx={{height:'100%'}}>
                                <Typography variant={'subtitle1'}>New Id Type</Typography>
                            </Grid>
                        </Grid>
                        <Grid item md={8} xl={8} xs={12}>
                            <TextField
                                disabled={loading}
                                id='input-new-id-type'
                                required
                                type={'text'}
                                onChange={(e) => {setNewIdType({...newIdType, name:e.target.value})}}
                                value={newIdType ? newIdType.name : ''}
                                sx={{ width: '100%' }}
                                inputProps={{maxLength: 128}}
                                placeholder='Id Type'
                            />
                        </Grid>
                    </Grid>
                </div>
                <Grid container direction='row'
                    justifyContent='flex-end'
                    alignItems='center'
                    spacing={2} sx={{marginTop:'20px'}} >
                    <Grid item>
                        <Button onClick={addIdTypeOnSubmit} variant='contained'>
                            Save
                        </Button>
                    </Grid>
                    <Grid item>
                        <Button onClick={addIdTypeOnClose} variant='outlined'>
                            Cancel
                        </Button>
                    </Grid>
                </Grid>
            </Box>
        </Modal>
    )
}