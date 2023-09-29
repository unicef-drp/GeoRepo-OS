import React, { useState, useEffect } from 'react';
import styled from '@mui/material/styles/styled';
import Tooltip, { TooltipProps, tooltipClasses } from '@mui/material/Tooltip';
import Skeleton from '@mui/material/Skeleton';
import Grid from '@mui/material/Grid';
import Typography from '@mui/material/Typography';
import Button from '@mui/material/Button';
import InfoIcon from '@mui/icons-material/Info';

const MAX_DESCRIPTION_LENGTH = 200;
const WINDOW_PREFERENCES: any = window.preferences
const HELP_BASE_URL = ''
const HelpTooltipCustom = styled(({ className, ...props }: TooltipProps) => (
    <Tooltip {...props} classes={{ popper: className }} />
  ))(({ theme }) => ({
    [`& .${tooltipClasses.tooltip}`]: {
      backgroundColor: '#fff',
      color: 'rgba(0, 0, 0, 0.87)',
      minWidth: 220,
      fontSize: theme.typography.pxToRem(12),
      border: '1px solid #dadde9',
      paddingTop: '10px'
    },
}))
const parseAnchorFromUrl = (url: string):string => {
    let _parts = url.split('#')
    return _parts.length > 1 ? _parts[1] : ''
}

interface HelpTooltipInterface {
    icon?: React.ReactElement,
    url: string
}

export default function HelpTooltip(props: HelpTooltipInterface) {
    const [loading, setLoading] = useState(true)
    const [title, setTitle] = useState('')
    const [desc, setDesc] = useState('')
    const helpFullUrl = `${HELP_BASE_URL}${props.url}`
    const anchorID = parseAnchorFromUrl(props.url)

    useEffect(() => {
        setLoading(true)
        fetch(helpFullUrl)
            .then(response => response.text())
            .then((response) => {
                const parser = new DOMParser()
                const htmlDoc = parser.parseFromString(response, 'text/html')
                const _helpTitleEl = htmlDoc.getElementById(anchorID)
                if (!_helpTitleEl) return
                setLoading(false)
                let _helpTitle = _helpTitleEl.innerText.replaceAll('¶', '')
                setTitle(_helpTitle)
                const _descEl = _helpTitleEl.nextElementSibling as HTMLElement
                if (_descEl && _descEl.innerText) {
                    setDesc(_descEl.innerText.length > MAX_DESCRIPTION_LENGTH ? `${_descEl.innerText.substring(0, MAX_DESCRIPTION_LENGTH)}...` : _descEl.innerText)
                }
            })
            .catch(err => {
                console.log(err)
                setLoading(false)
            })
    }, [])

    let _tooltipIcon = props.icon
    if (!_tooltipIcon) {
        _tooltipIcon = <InfoIcon fontSize="small" color="primary" />
    }
    return (
        <HelpTooltipCustom
            title={
                <React.Fragment>
                    <Grid container flexDirection={'column'} rowSpacing={2}>
                        <Grid item>
                            { loading && <Skeleton variant='rectangular' />}
                            { !loading && <Typography variant='h6' color="inherit">{title}</Typography> }
                        </Grid>
                        <Grid item>
                            { loading && <Skeleton variant='rectangular' height={'120px'} />}
                            { !loading && desc}
                        </Grid>
                        <Grid item container flexDirection={'row'} justifyContent={'flex-end'} sx={{marginTop: '20px'}}>
                            <Button variant='outlined' href={helpFullUrl} target='_blank'>Read more...</Button>
                        </Grid>
                    </Grid>
                </React.Fragment>
            }
        >
            { _tooltipIcon }
        </HelpTooltipCustom>
    )
}
