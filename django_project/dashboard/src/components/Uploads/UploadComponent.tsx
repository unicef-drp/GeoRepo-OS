import React from "react";
import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import Grid from "@mui/material/Grid";
import IconButton from "@mui/material/IconButton";
import Tooltip from "@mui/material/Tooltip";
import Typography from "@mui/material/Typography";
import LinearProgress from "@mui/material/LinearProgress";
import Button from "@mui/material/Button";
import ArrowCircleUpIcon from '@mui/icons-material/ArrowCircleUp';
import ArrowCircleDownIcon from '@mui/icons-material/ArrowCircleDown';


export const isFirstLevel = (level: string, isUploadLevel0: boolean): boolean => {
    if (isUploadLevel0)
      return level == '0'
    return level == '1'
}
  
export const isLastLevel = (level: string, totalLevel: number, isUploadLevel0: boolean): boolean => {
    if (isUploadLevel0)
        return parseInt(level) === totalLevel - 1
    return parseInt(level) == totalLevel
}

interface UploadComponentInterface {
    meta: any,
    fileWithMeta: any,
    isReadOnly: boolean,
    level: string,
    totalLevel: number,
    uploadLevel0: boolean,
    moveLevelUp?: (layerId: string) => void,
    moveLevelDown?: (layerId: string) => void,
    downloadLayerFile?: (layerId: string) => void
}

export default function UploadComponent(props: UploadComponentInterface)  {
    const meta = props.meta
    const fileWithMeta = props.fileWithMeta
    return (
      <Card sx={{ minWidth: 730, marginTop: 1 }}>
        <CardContent style={{ display: 'flex', flexDirection: 'row' , padding: '0px'}}>
          <Grid container>
            <Grid item padding='10px'>
              <Grid container flexDirection='column'>
                <IconButton aria-label="move up" size="medium" disabled={isFirstLevel(props.level, props.uploadLevel0) || props.isReadOnly} onClick={() => props.moveLevelUp(meta.id)}>
                  <Tooltip title="Move Up">
                    <ArrowCircleUpIcon />
                  </Tooltip>
                </IconButton>
                <IconButton aria-label="move down" size="medium" disabled={isLastLevel(props.level, props.totalLevel, props.uploadLevel0) || props.isReadOnly} onClick={() => props.moveLevelDown(meta.id)}>
                  <Tooltip title="Move Down">
                    <ArrowCircleDownIcon />
                  </Tooltip>
                </IconButton>
              </Grid>
            </Grid>
            <Grid item flexGrow={1}>
              <Grid container flexDirection='column'>
                <Grid container>
                  <Grid item xs={12} md={8} style={{ textAlign: 'left' }}>
                    <Typography sx={{ fontSize: 14 }} color='text.secondary' gutterBottom>
                      {meta.type}
                    </Typography>
                    <Typography variant="h6" component="div">
                      {meta.name}
                    </Typography>
                  </Grid>
                  <Grid item xs={12} md={4}>
                      <Typography sx={{ marginRight: 1 }} textAlign={'right'}>Level {props.level}</Typography>
                  </Grid>
                </Grid>
                <LinearProgress variant="determinate" value={meta.percent} sx={{ marginTop: 2 }} />
              </Grid>
            </Grid>
            <Grid item padding={'20px'}>
              <Grid container flexDirection='column'>
                <Grid container>
                  <Grid item xs={12} md={8}>
                    <div className={"button-container"}>
                      { !props.isReadOnly && (
                        <Button variant="outlined" color="error" onClick={() => fileWithMeta.remove()} sx={{ marginTop: 1 }}>
                          Remove
                        </Button>
                      )}
                      { props.isReadOnly && (
                        <Button variant="outlined" color="primary" onClick={() => props.downloadLayerFile(meta.id)} sx={{ marginTop: 1 }}>
                          Download
                        </Button>
                      )}
                    </div>
                  </Grid>
                </Grid>
              </Grid>
            </Grid>
          </Grid>
        </CardContent>
      </Card>
    )
}
