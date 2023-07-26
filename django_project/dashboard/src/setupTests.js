// jest-dom adds custom jest matchers for asserting on DOM nodes.
// allows you to do things like:
// expect(element).toHaveTextContent(/react/i)
// learn more: https://github.com/testing-library/jest-dom
import '@testing-library/jest-dom';
export const mockMapOn = jest.fn();
export const mockMapRemove = jest.fn();

jest.mock('maplibre-gl', () => ({
    Map: function () {
        this.on = mockMapOn;
        this.remove = mockMapRemove;
    }
}));
