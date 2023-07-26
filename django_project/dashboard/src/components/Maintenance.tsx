import React, {useEffect, useState, useRef} from "react";
import {
    Avatar,
    Collapse,
    Paper,
    Card,
    CardContent,
    Grid,
    Typography,
} from "@mui/material";
import ConstructionIcon from '@mui/icons-material/Construction';
import '../styles/Maintenance.scss';
import {useAppSelector} from "../app/hooks";
import {
    hasMaintenance,
    maintenanceMessage
} from "../reducers/maintenanceItem"

export default function Maintenance(props: any) {
    const open = useAppSelector(hasMaintenance)
    const message = useAppSelector(maintenanceMessage)

    return (
        <Collapse in={open} unmountOnExit sx={{flexShrink: 0}}>
            <Paper elevation={0}>
                <Card elevation={0}>
                    <CardContent className="MaintanceCardContent">
                        <Grid
                            container
                            wrap="nowrap"
                            spacing={2}
                            direction="row"
                            justifyContent="flex-start"
                            alignItems="center"
                            textAlign="left"
                        >
                            <Grid item>
                                <Avatar className="MaintenanceIcon">
                                    <ConstructionIcon fontSize="large" sx={{color:"black"}} />
                                </Avatar>
                            </Grid>

                            <Grid item>
                                <Typography variant="body2">
                                    { message && 
                                        <span dangerouslySetInnerHTML={{ __html: message }}></span>
                                    }
                                </Typography>
                            </Grid>
                        </Grid>
                    </CardContent>
                </Card>
        </Paper>
    </Collapse>
    )
}