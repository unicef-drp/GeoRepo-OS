import React from "react";
import loadable from '@loadable/component';
import {Typography} from "@mui/material";

const CircularProgress = loadable(
    () => import("@mui/material/CircularProgress" /* webpackChunkName: "loading" */), {
        fallback: <div>&nbsp;</div>
    }
)

interface LoadingInterface {
    label?: string,
    size?: number,
    color?: any,
    style?: any
}

export default function Loading(props: LoadingInterface) {
    return (
        <div className="loading-container">
            <CircularProgress size={props.size} color={props.color} style={props.style}/>
            { props.label ? <Typography sx={{ fontSize: 15 }} style={{ marginTop: 10 }}>{ props.label }</Typography> : '' }
        </div>
    )
}
