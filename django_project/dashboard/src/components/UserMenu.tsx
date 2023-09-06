/* ==========================================================================
   USER NAVBAR
   ========================================================================== */

import React, { Fragment, useState, useRef, RefObject} from 'react';
import Menu from '@mui/material/Menu';
import MenuItem from '@mui/material/MenuItem';
import SettingsIcon from '@mui/icons-material/Settings';
import HelpIcon from '@mui/icons-material/Help';
import Fade from '@mui/material/Fade';
import Box from '@mui/material/Box';

interface UserMenuInterface {
  helpPageRef?: RefObject<HTMLButtonElement>;
}


/**
 * User dropdown.
 **/
export default function UserMenu(props: UserMenuInterface) {
  console.log(props.helpPageRef?.current)
  const [anchorEl, setAnchorEl] = useState(null);
  const open = Boolean(anchorEl);
  const is_staff = (window as any).is_staff
  const username = (window as any).user_name
  const is_admin = (window as any).is_admin
  const handleClick = (event: any) => {
    setAnchorEl(event.currentTarget);
  };
  const handleClose = () => {
    setAnchorEl(null);
  };

  const getLoggedInName = () => {
    return username + ' (' + (is_admin?'Administrator':
        (is_staff?'Staff':'Member')
      ) +
      ')'
  }

  /**
   * Signin Modal Functions.
   **/
  const logoutUrl = (window as any).logoutURL; // eslint-disable-line no-undef

  // Admin URLS
  const adminUrl = '/admin/'; // eslint-disable-line no-undef
  // API Doc URLS
  const apiDocUrl = '/api/v1/docs/'; // eslint-disable-line no-undef
  const profileUrl = '/profile'

  if (username) {
    return (
      <div className='NavHeader-UserMenuContainer'>
        <Box className='NavHeader-Username' sx={{display:{xs:'none', sm: 'flex'}}}>{getLoggedInName()}</Box>
        <div className='HelpButton .SvgButton'>
          <a href='#' onClick={_ => {
            // @ts-ignore
            props.helpPageRef.current?.open()
          }}>
            <HelpIcon/>
          </a>
        </div>
        <div>
          <button onClick={handleClick} type="button">
            <SettingsIcon/>
          </button>
        </div>
        <Menu
          anchorEl={anchorEl}
          open={open}
          onClose={handleClose}
          MenuListProps={{
            'aria-labelledby': 'basic-button',
          }}
          TransitionComponent={Fade}
          className='UserMenu-Links'
        >
          <MenuItem className='MenuItem-Header'>
            <span>v{(window as any).georepoCodeVersion}</span>
          </MenuItem>
          <MenuItem className='MenuItem-Header'>
            <a href={profileUrl}>Profile</a>
          </MenuItem>
          <MenuItem className='MenuItem-Header'>
            <a href={apiDocUrl}>API Docs</a>
          </MenuItem>
          {
            is_staff ? (
              <MenuItem className='MenuItem-Header'>
                <a href={adminUrl}>Django Admin</a>
              </MenuItem>
            ) : ''
          }
          <MenuItem className='MenuItem-Header'>
            <a href={logoutUrl}>Logout</a>
          </MenuItem>
        </Menu>
      </div>
    )
  } else {
    return (
      <Fragment>
        <a href={'#'}>
          <button type='button'>
            LOG IN
          </button>
        </a>
      </Fragment>
    );
  }
}
