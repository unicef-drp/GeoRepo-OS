import React from 'react';
import SideNavigation from "./SideNavigation";
import {
  BrowserRouter as Router
} from "react-router-dom";
import {render} from "@testing-library/react";
import {routes} from "../views/routes";

it('renders side navigations', () => {
  const { container } = render(
    <Router>
      <SideNavigation routes={routes}/>
    </Router>
  );
  expect(container.getElementsByClassName(
    'SideNavigation-Row').length
  ).toBeGreaterThan(1);
})
