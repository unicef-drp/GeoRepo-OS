import {routes} from "./routes";
import {headerButtons} from "./HeaderButtons";

export function moduleApp() {
  return {
    'name': 'admin_boundaries',
    'routes': routes,
    'headers': headerButtons
  }
}
