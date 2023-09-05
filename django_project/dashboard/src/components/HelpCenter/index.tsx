import React, {
  forwardRef,
  useEffect,
  useImperativeHandle,
  useState,
  PropsWithChildren
} from 'react';
import { Button } from "@mui/material";

import Block from "./Block";
import ChatBubbleIcon from '@mui/icons-material/ChatBubble';
import CloseIcon from '@mui/icons-material/Close';
import EmailIcon from '@mui/icons-material/Email';

import './style.scss';
import CircularProgress from "@mui/material/CircularProgress";
import {AccessRequestDetailInterface} from "../../models/access";
import {MUIDataTableColumnDef} from "mui-datatables";
import {GridSortingInitialState} from "@mui/x-data-grid";
import {ExpandedRowInterface, RowData} from "../Table";

interface AdminTableInterface {
  children?: React.ReactNode;
  tabIndex: number;
  variant: String;
  disabled: boolean;
  className?: String;
}


function ThemeButton({children, tabIndex, variant, disabled, className}: AdminTableInterface) {
  return (
    <Button
      tabIndex={tabIndex}
      disabled={disabled}
      className={'ThemeButton ' + (className ? className : '')}>
      {children}
    </Button>
  )
}

// @ts-ignore
/** Help center section */

export const HelpCenter = forwardRef(({}, ref) =>
{
    const [open, setOpen] = useState(false)
    const [loading, setLoading] = useState(true)
    const [data, setData] = useState(null)

    useImperativeHandle(ref, () => ({
      open() {
        return setOpen(_ => !_)
      }
    }));

    useEffect(
      () => {
        setLoading(true)
        fetch(`/docs/data?relative_url=` + window.location.pathname,)
          .then(response => response.json())
          .then((response) => {
            if (response.detail) {
              throw new Error(response.detail)
            }
            setLoading(false)
            setData(response)
          })
          .catch(err => {
            setLoading(false)
          })
      }, [])

    return <div
      className={'HelpCenter ' + (open ? 'Open' : '')}
      onClick={_ => {
        setOpen(false)
      }}>
      <div className='HelpCenter-Content' onClick={_ => {
        _.stopPropagation();
      }}>
        <div className='HelpCenter-Close'>
          <CloseIcon
            onClick={_ => {
              setOpen(false)
            }}/>
        </div>

        {/* -------------------------------- */}
        {/* CONTENT */}
        <div className='HelpCenter-InnerContent'>
          {
            loading ? <div className='Throbber'>
              <CircularProgress/> Loading...
            </div> : data ? <Block data={data} isRoot={true}/> :
              <div className='NotFound'>No helps found</div>
          }
        </div>
        {/* -------------------------------- */}
        <div className='HelpCenter-Footer'>
          <a
            tabIndex={-1}
            href='#'>
            <ThemeButton
              tabIndex={-1}
              variant="basic Basic"
              disabled={true}
            >
              <EmailIcon/> Send Feedback
            </ThemeButton>
          </a>
          <a
            tabIndex={-1}
            href='#'>
            <ThemeButton
              tabIndex={-1}
              variant="basic Basic"
              disabled={true}
            >
              <ChatBubbleIcon/> Contact Us
            </ThemeButton>
          </a>
        </div>
      </div>
    </div>
  }
)