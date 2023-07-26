import React, {} from "react";
import '../styles/NavBar.scss';
import UserMenu from "./UserMenu";
import Grid from '@mui/material/Grid';


export default function NavBar() {

  return (
    <header>
      <div className='NavHeader'>
        <Grid container className='NavHeader Menu' sx={{flexWrap:0}}>
          <Grid item className='NavHeaderLogo' sx={{display:'block', height:'100%'}}>
            <a
              href='/'
              title={'Homepage'}
              className='nav-header-link'
            >
                <img src='/static/unicef_logo.png' alt="Logo"/>
            </a>
          </Grid>
          <Grid item className="NavHeaderSeparator" sx={{display:{xs:'none', sm: 'flex'}}}>
            <div></div>
          </Grid>
          <Grid item className='NavHeaderTitle' sx={{display:{xs:'none', sm: 'flex'}}}>
            <button type='button'>
              <a
                href='/'
                title='Homepage'
                className='NavHeaderLink'
              >
                GeoRepo
              </a>
            </button>
          </Grid>
          <Grid item className="NavHeaderRight" sx={{flexGrow:{xs:1, sm: 0}, paddingRight:{xs:0, sm: '1.5rem'} }}>
              <div className="NavHeader-Options">
                <UserMenu />
              </div>
          </Grid>
        </Grid>
      </div>
    </header>
  )
}
