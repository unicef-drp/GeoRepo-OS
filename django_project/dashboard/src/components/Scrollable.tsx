import React from 'react';


interface ScrollableProps {
    children?: React.ReactNode;
  }

export default function Scrollable(props: ScrollableProps) {
    return (  
        <div style={{position: 'relative', height: '100%'}}>
            <div style={{position: 'absolute', top: 0, bottom: 0, left: 0, right: 0, display: 'flex', flexDirection: 'column', flexGrow: 1}}>
                {props.children}
            </div>
        </div>
    )
}