import React, {useEffect, Suspense, useRef} from 'react';
import 'react-quill/dist/quill.snow.css';

const ReactQuill = React.lazy(() => import('react-quill'))

import { Quill } from 'react-quill';
import Loading from "./Loading";
const Delta = Quill.import('delta')
let Inline = Quill.import('blots/inline')

class SpanBlot extends Inline {
    static blotName = 'tag';
    static tagName = 'span'
    static className = 'keyword'

    static formats(): boolean {
        return true;
    }
}
SpanBlot.blotName = 'span';
SpanBlot.tagName = 'span';
SpanBlot.className = 'keyword'
Quill.register('formats/span', SpanBlot)

export default function TReactQuill(props: any) {
    const quill = props.quillRef ? props.quillRef : useRef()
    const quillContainer = props.quillContainerRef ? props.quillContainerRef : useRef()

    useEffect(() => {
        if (quill.current) {
            // @ts-ignore
            const _quill = (quill as any).current.getEditor();
            _quill.clipboard.addMatcher(Node.ELEMENT_NODE, (node: any, delta: any) => {
                return delta.compose(new Delta().retain(delta.length(),
                { color: false,
                    background: false,
                    bold: false,
                    strike: false,
                    underline: false
                }
                ));
              })
        }
    }, [quill.current])

    return (
        <Suspense fallback={<Loading />}>
            <div ref={quillContainer}>
                <ReactQuill
                    ref={quill}
                    formats={['formats/span', 'span', 'id', 'bold']}
                    modules={props.modules}
                    theme='snow'
                    value={props.value}
                    onChange={props.onChange}
                    style={props.style}
                    onKeyDown={props.onKeyDown}
                    readOnly={props.readOnly}
                />
            </div>
        </Suspense>
    )
}
