import React from 'react';
import Grid from '@mui/material/Grid';
import Link from '@mui/material/Link';
import Typography from '@mui/material/Typography';

export default function InvalidPermission(props: any) {

    return (
        <div style={{display:'flex', flex: 1, flexDirection: 'column'}}>
            <Grid container flexDirection={'row'} justifyContent={'center'}>
                <Grid item>
                    <Typography variant='h4'>Invalid Permissions</Typography>
                </Grid>
            </Grid>
            <Grid container flexDirection={'row'} justifyContent={'center'} sx={{mt:'20px'}}>
                <Grid item>
                    <Typography variant='h6'>
                        You do not have access to this page. Click <Link href="/" underline="none">here</Link> to go back to dashboard.
                    </Typography>
                </Grid>
            </Grid>
        </div>
    )
}
