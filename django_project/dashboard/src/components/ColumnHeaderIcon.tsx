import React from 'react'
import Grid from '@mui/material/Grid'
import HtmlTooltip from './HtmlTooltip';

interface ColumnHeaderIconInterface {
    title: string,
    icon?: React.ReactElement,
    tooltipDescription: React.ReactElement,
    tooltipTitle?: string,
    alignStart?: boolean
}

export default function ColumnHeaderIcon(props: ColumnHeaderIconInterface) {
    return (
        // <Grid display='flex'>
        //     <Grid item display='flex'>
        //         <Grid display='flex' flexDirection='row' justifyContent='center' alignItems={props.alignStart?'flex-start':'center'}>
                    <span>
                    <span>{props.title}</span>
                    <HtmlTooltip
                        tooltipTitle={props.tooltipTitle} tooltipDescription={props.tooltipDescription}
                        icon={props.icon}
                    />
                    </span>
        //         </Grid>
        //     </Grid>
        // </Grid>
    )
}