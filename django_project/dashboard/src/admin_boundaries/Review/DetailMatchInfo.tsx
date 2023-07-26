import React from 'react';
import {
    Grid,
    LinearProgress,
    Skeleton,
    TableCell,
    TableRow,
    Typography,
    Button
} from "@mui/material";


export default function DetailMatchInfo(props: any) {
    const geometrySimilarity = (props.rowData[10] + props.rowData[11]) / 2
    const ActionButton = props.actionButton
    const FooterMatchInfo = props.matchInfoFooter
    return (
        <TableRow className='detail-match-info'>
            <TableCell colSpan={13}>
                <LinearProgress variant="determinate" value={geometrySimilarity} style={{ height: 20, borderRadius: 5 }}/>
                <Typography className={'overlap-title'}>Overlap: {geometrySimilarity}%</Typography>
                <Grid container spacing={2} style={{ marginTop: 5 }}>
                    <Grid item md={4} xs={12}>
                        { props.actionButton && (
                            <ActionButton {...props.rowData} />
                        )}
                    </Grid>
                    <Grid item md={4} xs={12}>
                        <Typography className="main-boundary-text">Main Boundary</Typography>
                        {props.loading || !props.mainBoundary ?  <Skeleton variant="rectangular" height={20} width={40}/> : props.mainBoundary.label}
                    </Grid>
                    <Grid item md={4} xs={12}>
                        <Typography className="comparison-boundary-text">Comparison Boundary</Typography>
                        {props.loading || !props.comparisonBoundary ?  <Skeleton variant="rectangular" height={20} width={40}/> : props.comparisonBoundary.label }
                    </Grid>
                </Grid>
                <Grid container spacing={2} style={{ marginTop: 2 }}>
                    <Grid item md={4} xs={12}>
                        Area
                    </Grid>
                    <Grid item md={4} xs={12}>
                        <Grid container>
                            {props.loading || !props.mainBoundary ?  <Skeleton variant="rectangular" height={20} width={40}/> : props.mainBoundary.area + ' km2'}
                        </Grid>
                    </Grid>
                    <Grid item md={4} xs={12}>
                        <Grid container>
                            {props.loading || !props.comparisonBoundary ?  <Skeleton variant="rectangular" height={20} width={40}/> : props.comparisonBoundary.area  + ' km2'}
                        </Grid>
                    </Grid>
                </Grid>
                <Grid container spacing={2} style={{ marginTop: 2 }}>
                    <Grid item md={4} xs={12}>
                        Perimeter
                    </Grid>
                    <Grid item md={4} xs={12}>
                        <Grid container>
                            {props.loading || !props.mainBoundary ?  <Skeleton variant="rectangular" height={20} width={40}/> : props.mainBoundary.perimeter }
                        </Grid>
                    </Grid>
                    <Grid item md={4} xs={12}>
                        <Grid container>
                            {props.loading || !props.comparisonBoundary ?  <Skeleton variant="rectangular" height={20} width={40}/> : props.comparisonBoundary.perimeter }
                        </Grid>
                    </Grid>
                </Grid>
                {FooterMatchInfo && (
                    <Grid container spacing={2} style={{ marginTop: 2 }}>
                        <Grid item md={4} xs={12}>
                            <FooterMatchInfo {...props.rowData} />
                        </Grid>
                        <Grid item md={4} xs={12}>
                        </Grid>
                        <Grid item md={4} xs={12}>
                        </Grid>
                    </Grid>
                )}
            </TableCell>
        </TableRow>
    )
}
