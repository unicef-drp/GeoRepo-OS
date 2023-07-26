import React from 'react'
import styled from '@mui/material/styles/styled'
import Tooltip, { TooltipProps, tooltipClasses } from '@mui/material/Tooltip'
import Typography from '@mui/material/Typography';
import InfoIcon from '@mui/icons-material/Info';

const HtmlTooltipCustom = styled(({ className, ...props }: TooltipProps) => (
    <Tooltip {...props} classes={{ popper: className }} />
  ))(({ theme }) => ({
    [`& .${tooltipClasses.tooltip}`]: {
      backgroundColor: '#f5f5f9',
      color: 'rgba(0, 0, 0, 0.87)',
      maxWidth: 220,
      fontSize: theme.typography.pxToRem(12),
      border: '1px solid #dadde9',
    },
  }))

interface HtmlTooltipInterface {
    tooltipDescription: React.ReactElement,
    icon?: React.ReactElement,
    tooltipTitle?: string,
}

export default function HtmlTooltip(props: HtmlTooltipInterface) {
    let tooltipIcon = props.icon
    if (!tooltipIcon) {
        tooltipIcon = <InfoIcon fontSize="small" color="primary" />
    }

    return (
        <HtmlTooltipCustom
            title={
                <React.Fragment>
                    {props.tooltipTitle &&  <Typography color="inherit">{props.tooltipTitle}</Typography> }
                    {props.tooltipDescription}
                </React.Fragment>
            }
        >
            {tooltipIcon}
        </HtmlTooltipCustom>
    )
}