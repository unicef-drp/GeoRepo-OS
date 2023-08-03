import axios from "axios";

axios.defaults.headers.common = {
    'X-CSRFToken' : (window as any).csrfToken
}

let controller:AbortController = null;

/**
 * Fetch data with axios, abort existing ongoing request if requested
 */
export const fetchData = async function (
  url: string,
  abortPrevious: boolean = true
) {
    if (!controller) {
        controller = new AbortController()
    } else {
        if (abortPrevious) {
            controller.abort()
        }
        controller = new AbortController()
    }
    return axios.get(url, {
        signal: controller.signal
    })
}

/**
 * Perform Fetching Data
 *
 * @param {string} url Url to query
 * @param {object} options Options of request
 * @param {object} params Params
 * @param {Function} receiveAction Function on receiving data
 * @param {boolean} useCache Force to use cache or not
 */
export const fetchingData = async function (
    url: string,
    params: Object,
    options: Object,
    receiveAction?: (arg0: any, arg1: any) => void,
    useCache: boolean = true
): Promise<{ responseData: any, responseStatus: string, responseStatusCode?: number }> {
    if (params && Object.keys(params).length) {
        const paramsUrl = [];
        for (const [key, value] of Object.entries(params)) {
            paramsUrl.push(`${key}=${value}`)
        }
        url += '?' + paramsUrl.join('&')
    }
    try {
        return {
            responseData: await fetchJSON(url, options, useCache),
            responseStatus: 'success'
        };
    } catch (error) {
        let responseStatusCode = 400
        if (error instanceof RequestError) {
            responseStatusCode = error.statusCode
        }
        return {
            responseData: null,
            responseStatus: 'failed',
            responseStatusCode: responseStatusCode
        };
    }
}

/**
 * Perform request to fetch json
 *
 * @param {string} url Url to query
 * @param {object} options Options for fetch
 */
// TODO:
//  Make cache in elegant way
const responseCaches:any = {}

class RequestError extends Error {
    statusCode: number;
    constructor(message: string, statusCode: number) {
      super(message);
      this.name = "RequestError";
      this.statusCode = statusCode;

      Object.setPrototypeOf(this, RequestError.prototype);
    }
}

const handleError = (message: string, statusCode?: number) => {
    if (statusCode) {
        throw new RequestError(message, statusCode)
    } else {
        throw Error(message)
    }
}

export async function fetchJSON(
        url: string,
        options: Object,
        useCache: boolean = true
    ) {
    if (!useCache) {
        responseCaches[url] = null
    }
    if (!responseCaches[url]) {
        try {
            const response = await fetch(url, options);
            let json: { detail: string; message: string };
            try {
                json = await response.json();
            } catch (error) {
                json = {
                    message: response.status + ' ' + response.statusText,
                    detail: response.status + ' ' + response.statusText
                }
            }
            if (response.status >= 400) {
                handleError(json.message, response.status)
            }
            responseCaches[url] = json;
            return json;
        } catch (error: any) {
            if (error instanceof RequestError) {
                handleError(error.message, error.statusCode)
            } else {
                handleError(error.message)
            }            
        }
    } else {
        return responseCaches[url]
    }
}

/**
 * Perform Pushing Data Using POST method
 *
 * @param {string} url Url to query
 * @param {object} data Data to be pushed
 */
export const postData = async function (
    url: string,
    data: any ) {
    return axios.post(url, data)
};

/**
 * Perform Pushing Data Uing PUT method
 *
 * @param {string} url Url to query
 * @param {object} data Data to be pushed
 */
export const putData = async function (
    url: string,
    data: any ) {
    return axios.put(url, data)
};

/**
 * Post JSON Data
 *
 * @param {string} url Url to query
 * @param {BodyInit} data Data to be pushed
 */
export async function postJSON(url: string, data: any) {
    try {
        return await fetch(url, {
            method: 'POST', headers: {
                'X-CSRFToken': (window as any).csrfToken,
                'Accept': 'application/json',
                'Content-Type': 'application/json'
            }, body: data
        }).then(function (response) {
            console.log(response)
            if (response.status < 400) {
                handleError(response.statusText)
            } else {
                if (response.status === 400) {
                    return response.json();
                } else {
                    handleError(response.statusText, response.status)
                }
            }
        }).then(function (response) {
            return response
        });
    } catch (error) {
        throw error;
    }
}

export interface LanguageOption {
    id: string,
    name: string,
    code?: string
}

export const fetchLanguages = async () : Promise<LanguageOption[]> => {
    return axios.get('/api/language/list/').then(
      (response: any) => response.data,
      (error: any) => {
          throw new Error(error)
      }
    )
}
