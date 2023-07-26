import React from 'react';
import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';


interface EmptyTabPanelInterface {
    text: string;
}

export default function EmptyTabPanel(props: EmptyTabPanelInterface) {
    return (
        <Box sx={{display:'flex', flex: 1, flexDirection: 'column', flexGrow: 1, height: '100%', padding: '10px'}}>
            <Typography>{props.text}</Typography>
        </Box>
    )
}

