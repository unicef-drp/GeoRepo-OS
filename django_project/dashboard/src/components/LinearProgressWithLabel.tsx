import * as React from 'react';
import LinearProgress, { LinearProgressProps } from '@mui/material/LinearProgress';
import Typography from '@mui/material/Typography';
import Grid from '@mui/material/Grid';

export default function LinearProgressWithLabel(props: LinearProgressProps & { value: number, maxBarWidth?: string }) {
  const {maxBarWidth, ...oriProps} = props
  const width = maxBarWidth || '100%'
  return (
    <Grid sx={{ display: 'flex', alignItems: 'center' }}>
      <Grid sx={{ width: width, mr: 1 }}>
        <LinearProgress variant="determinate" {...oriProps} />
      </Grid>
      <Grid sx={{ minWidth: 35 }}>
        <Typography variant="body2" color="text.secondary">{`${Math.round(
          props.value,
        )}%`}</Typography>
      </Grid>
    </Grid>
  );
}