
export interface SortOrderInterface {
    name?: string,
    direction?: string,
}

export default interface PaginationInterface {
    page: number,
    rowsPerPage: number,
    sortOrder: SortOrderInterface,
}

export const getDefaultPagination = ():PaginationInterface => {
    return {
        page: 0, // mui datatable also starts from 0, API might start from 1
        rowsPerPage: 10,
        sortOrder: {}
    }
}

export const rowsPerPageOptions = [10, 15, 20, 25]
