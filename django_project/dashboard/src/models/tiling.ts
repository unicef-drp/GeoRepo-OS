export interface AdminLevelTiling {
    level: number,
    simplify_tolerance: number
}

export interface TilingConfig {
    zoom_level: number,
    admin_level_tiling_configs: AdminLevelTiling[]
}

export const MAX_ZOOM = 14
export const ZOOM_LEVELS = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14]