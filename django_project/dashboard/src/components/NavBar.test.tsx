import React from 'react';
import {render} from "@testing-library/react";
import NavBar from "./NavBar";

it('renders navbar from site preferences', () => {
  window.preferences = {
    'site_title': 'Site Test'
  }

  const { getByText } = render(
    <NavBar/>
  )

  expect(getByText('LOG IN')).toBeInTheDocument();
})
