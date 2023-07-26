/* ==========================================================================
   LINKS NAVBAR
   ========================================================================== */

import React, { useState } from 'react';
import MenuItem from '@mui/material/MenuItem';
import Menu from "@mui/material/Menu";
import KeyboardArrowDownIcon from '@mui/icons-material/KeyboardArrowDown';
import Fade from '@mui/material/Fade';

/**
 * Link dropdown.
 * **/
export default function Links() {
  const navbarLinks: any[] = [
    {
      'url': '/admin',
      'name': 'Django Admin'
    },
    {
      'url': '/docs',
      'name': 'API Docs'
    }
  ];
  const [anchorEl, setAnchorEl] = useState(null);
  const open = Boolean(anchorEl);
  const handleClick = (event: { currentTarget: any; }) => {
    setAnchorEl(event.currentTarget);
  };
  const handleClose = () => {
    setAnchorEl(null);
  };
  return (
    <div>
      <button onClick={handleClick} type="button">
        <div className='NavHeader-Options'>
          <div>LINKS</div>
          <div className='NavHeader-Options-Icon'><KeyboardArrowDownIcon/>
          </div>
        </div>
      </button>
      <Menu
        anchorEl={anchorEl}
        open={open}
        onClose={handleClose}
        MenuListProps={{
          'aria-labelledby': 'basic-button',
        }}
        TransitionComponent={Fade}
      >
        {
          navbarLinks.map(
            (link, index) => (
              <MenuItem key={index} className='MenuItem-Header'>
                <a href={link.url}>{link.name}</a>
              </MenuItem>
            )
          )
        }
      </Menu>
    </div>
  )
}
