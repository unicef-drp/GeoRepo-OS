import {routes} from "./routes";
import {headerButtons} from "./HeaderButtons";

export function moduleApp() {
  return {
    'name': 'boundary_lines',
    'routes': routes,
    'headers': headerButtons
  }
}
