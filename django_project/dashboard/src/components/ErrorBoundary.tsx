import React from "react";

export default class ErrorBoundary extends React.Component {
  constructor(props: any) {
    super(props);
    this.state = { error: null, errorInfo: null };
  }

  componentDidCatch(error: any, errorInfo: any) {
    // You can also log the error to an error reporting service
     this.setState({
      error: error,
      errorInfo: errorInfo
    })
  }

  render() {
    // @ts-ignore
    if (this.state.errorInfo) {
      // You can render any custom fallback UI
      return <div className="FormContainer">
        <h2>Something went wrong...</h2>
        { process.env.NODE_ENV && process.env.NODE_ENV === 'development' ?
          <details style={{whiteSpace: 'pre-wrap', textAlign: 'left', color: 'red'}}>
              <pre>
              {(this.state as any).error && (this.state as any).error.toString()}
                <br/>
                {(this.state as any).errorInfo.componentStack}
               </pre>
          </details> : null }
      </div>;
    }

    return this.props.children;
  }
}
