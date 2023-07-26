import React, {useEffect, useRef, useLayoutEffect} from 'react';

export interface ResizeEventInterface {
    containerRef: any,
    onBeforeResize: () => void,
    onResize: (clientHeight:number) => void,
    forceUpdate?: Date
}

export default function ResizeTableEvent(props: ResizeEventInterface) {
    const windowResizeTimeoutRef = useRef(null)

    const updateTableSize = () => {
        // before resizing trigger table height to be 0
        if (props.containerRef && props.containerRef.current) {
            props.onBeforeResize()
        }
        if (windowResizeTimeoutRef.current) clearTimeout(windowResizeTimeoutRef.current)
        windowResizeTimeoutRef.current = setTimeout(() => {
            if (props.containerRef && props.containerRef.current) {
                props.onResize(props.containerRef.current.clientHeight)
            }
        }, 200)
    }

    useEffect(() => {
        if (props.forceUpdate)
            updateTableSize()
    }, [props.forceUpdate])

    useLayoutEffect(() => {
        window.addEventListener('resize', updateTableSize)
        updateTableSize()
        return () => window.removeEventListener('resize', updateTableSize)
    }, [])

    return (<div></div>)
}
